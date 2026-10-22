"""Simulate an instrument into McStas NeXus (HDF5) output, read with `nexus_io.read_scan`.

A `Simulation` holds the instrument to simulate and the folder its runs write to:

- `run`: one run, source -> detector;
- `scan`: a run per value of an instrument parameter, source -> detector, the values in parallel;
- `run_to_sample`: source -> `sample_pos` once, the beam dumped into an MCPL beam file;
- `run_from_sample`: one run from that beam file, `sample_pos` -> detector;
- `scan_from_sample`: a run per value from that beam file, the values in parallel.

Everything runs through McStasScript's public API (`settings`, `set_parameters`, `run_to`,
`run_from`, `backengine`); a scan is a `backengine` per value, merged into one file.
"""

import copy
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from mcstas_to_sqe.mcstas.builder import build_mcstas, default_input_dir
from mcstas_to_sqe.mcstas.nexus_io import merge_entries
from mcstas_to_sqe.mcstas.run_folders import default_output_dir, latest_beam, run_folder


def _run_points(inst, output_path, points, seed=None, n_jobs: int | None = None):
    """Run `inst` once per point (instrument parameter values, McStas name -> value), `n_jobs`
    at a time (None: all cores), and merge the outputs into `output_path/mccode.h5`, an entry
    per point in the order of `points`, which is returned.

    Each point runs a copy of `inst`, with its own values, output folder and random seed (`seed`
    + index, default: a random `seed`), so the runs do not repeat each other's random numbers.
    The first point writes and compiles the instrument (its values the defaults), the others
    reuse it.
    """
    output_path.mkdir()  # holds a folder per point
    if seed is None:
        seed = int(np.random.SeedSequence().generate_state(1)[0] % 10**9)
    folders = [output_path / f"point_{n:04d}" for n in range(len(points))]

    runs = []
    for n, (values, folder) in enumerate(zip(points, folders)):
        run = copy.deepcopy(inst)  # a run's settings and values stay its own
        run.settings(
            output_path=str(folder),
            seed=seed + n + 1,  # mcrun does not accept seed 0
            force_compile=n == 0,
        )
        run.set_parameters(**values)
        runs.append(run)

    runs[0].backengine()  # compile once, on the first point
    with ThreadPoolExecutor(max_workers=n_jobs or os.cpu_count()) as pool:
        list(pool.map(lambda run: run.backengine(), runs[1:]))  # each a separate mcrun process

    merged = merge_entries([folder / "mccode.h5" for folder in folders], output_path / "mccode.h5")
    for folder in folders:
        shutil.rmtree(folder)
    return merged


class Simulation:
    """Runs of `instrument` (e.g. a `SingleCrystalDiffractometer`), each into a new folder of
    `output_dir`, named by its start time and mode: `<time>_run`, `<time>_scan_<variable>`,
    `<time>_run_to_sample`, `<time>_run_from_sample` and `<time>_scan_<variable>_from_sample`,
    with `<time>` e.g. `20261022-143005`. A `folder_name` gives the folder instead, which is then
    replaced on every run. `run_folders.clean_runs` removes the older runs, never a
    `run_to_sample` one. Every run builds the instrument anew, into `input_dir`, so a change to
    it applies to the next run.

    Both folders are in `work_dir` (None for `default_work_dir()`: the current folder, or
    MCSTAS_TO_SQE_WORKDIR), fixed when the simulation is created: `mcstas_output/` and
    `mcstas_input/<instrument name>/`. `output_dir` and `input_dir` put either elsewhere.

    `instr_params` of a run are its instrument parameters, by McStas name: omega, chi, phi (deg;
    the instrument's unless given), and the `wavelength` (angstrom; the one of the instrument's
    ei unless given). A scan gives its `variable`, one of them, a run per value of `values`, all
    into one `mccode.h5` with an entry per value (`entry1`, `entry2`, ... in their order).

    `beam_file` is the beam file the runs from the sample start from: the one of the last
    `run_to_sample`, else the newest `beam.mcpl.gz` in `output_dir`, so a beam dumped in an earlier
    session is found (None if there is none).
    """

    def __init__(self, instrument, output_dir=None, input_dir=None, work_dir=None):
        self.instrument = instrument
        self.output_dir = Path(output_dir or default_output_dir(work_dir))
        self.input_dir = Path(input_dir or default_input_dir(instrument, work_dir))
        self.beam_file = latest_beam(self.output_dir)

    def _build(self, **settings):
        """Return the McStasScript instrument, with NeXus output and the other run `settings`."""
        inst = build_mcstas(self.instrument, input_path=self.input_dir)
        inst.settings(NeXus=True, increment_folder_name=False, suppress_output=True, **settings)
        return inst

    def _build_from_sample(self, beam_file, **settings):
        """Return the McStasScript instrument from `sample_pos` on, starting from `beam_file`
        (None: the simulation's). Single process: with MPI the ranks would all repeat the same
        neutrons of the beam file."""
        beam_file = beam_file or self.beam_file
        if beam_file is None:
            raise FileNotFoundError(f"no beam file in {self.output_dir}: run run_to_sample first")
        beam_file = Path(beam_file).resolve()
        inst = self._build(mpi=None, **settings)
        inst.run_from(self.instrument.sample_pos.name, filename=f'"{beam_file}"')
        return inst

    def _get_params(self, instr_params):
        """The instrument parameter values (McStas name -> value) of a run: the instrument's,
        with `instr_params` in place, one number each.

        >>> from mcstas_to_sqe.instruments import Params, SingleCrystalDiffractometer
        >>> sim = Simulation(SingleCrystalDiffractometer(params=Params(omega=30)))
        >>> sim._get_params({})  # the instrument's
        {'wavelength': 2.4172624717111, 'omega': 30, 'chi': 0.0, 'phi': 0.0}
        >>> sim._get_params({"chi": 1})  # chi in place
        {'wavelength': 2.4172624717111, 'omega': 30, 'chi': 1, 'phi': 0.0}
        >>> sim._get_params({"omega": [1, 2]})
        Traceback (most recent call last):
        ValueError: ['omega']: one number each; scan a variable with a scan
        >>> sim._get_params({"omgea": 3})
        Traceback (most recent call last):
        ValueError: no instrument parameter ['omgea'], only ['chi', 'omega', 'phi', 'wavelength']
        """
        values = {p.name: p.value for p in self.instrument.instr_params}
        if unknown := sorted(instr_params.keys() - values.keys()):
            raise ValueError(f"no instrument parameter {unknown}, only {sorted(values)}")
        if many := [k for k, v in instr_params.items() if isinstance(v, str) or np.ndim(v) > 0]:
            raise ValueError(f"{many}: one number each; scan a variable with a scan")
        return values | instr_params

    def _points(self, variable, values, instr_params):
        """The instrument parameter values of each run of a scan of `variable` over `values`."""
        fixed = self._get_params({**instr_params, variable: 0.0})
        return [fixed | {variable: value} for value in np.asarray(values, dtype=float).tolist()]

    def run(
        self, folder_name=None, ncount=1e7, seed=None, mpi="auto", custom_flags=None, **instr_params
    ):
        """Run source -> detector once, with `instr_params`. Output goes to
        `output_dir/<time>_run/mccode.h5` (or `folder_name/`), which is returned. `custom_flags`
        is passed to mcrun."""
        output_path = run_folder(self.output_dir, folder_name, "run")
        inst = self._build(
            output_path=str(output_path),
            ncount=ncount,
            mpi=mpi,
            force_compile=True,
            seed=seed,
            custom_flags=custom_flags,
        )
        params = self._get_params(instr_params)
        inst.set_parameters(**params)
        inst.backengine()  # compiles in its input_dir
        return output_path / "mccode.h5"

    def scan(
        self,
        variable,
        values,
        folder_name=None,
        ncount=1e7,
        n_jobs=None,
        seed=None,
        custom_flags=None,
        **instr_params,
    ):
        """Run source -> detector for every value of `variable` (e.g. "omega",
        np.linspace(-48, 83, 11)), the values in parallel (`n_jobs` single-process mcrun jobs at
        a time, default: all cores); the other instrument parameters are `instr_params`. Returns
        `output_dir/<time>_scan_<variable>/mccode.h5` (or `folder_name/`), an entry per value.
        Each value gets its own random seed (`seed` + index), so the jobs do not repeat each
        other's random numbers."""
        points = self._points(variable, values, instr_params)  # checks `variable` names a parameter
        output_path = run_folder(self.output_dir, folder_name, f"scan_{variable}")
        inst = self._build(ncount=ncount, mpi=None, custom_flags=custom_flags)
        return _run_points(inst, output_path, points, seed=seed, n_jobs=n_jobs)

    def run_to_sample(self, folder_name=None, ncount=1e8, mpi="auto", **instr_params):
        """Part 1 of a split run: simulate source -> slit -> incident monitor -> `sample_pos` and
        dump the beam to an MCPL file. Run it once with a large `ncount`. Returns the path of the
        beam file (`output_dir/<time>_run_to_sample/beam.mcpl.gz`, or `folder_name/`), which becomes
        `beam_file`; the folder also has `mccode.h5` with the incident monitor.

        The beam file only fits instruments with the same source and beam geometry, and the same
        wavelength, so make a new one if you change the instrument's ei, source, slit or monitor
        settings.
        """
        output_path = run_folder(self.output_dir, folder_name, "run_to_sample")
        inst = self._build(output_path=str(output_path), ncount=ncount, mpi=mpi, force_compile=True)
        params = self._get_params(instr_params)
        inst.set_parameters(**params)
        inst.run_to(
            self.instrument.sample_pos.name,
            run_name="beam",
            comment=f"{ncount:g} neutrons",
            filename='"beam.mcpl"',
        )
        inst.backengine()
        self.beam_file = output_path / "beam.mcpl.gz"
        return self.beam_file

    def run_from_sample(self, folder_name=None, beam_file=None, seed=None, **instr_params):
        """Part 2 of a split run, any time later (even in another session): simulate
        `sample_pos` -> sample -> detector once, starting from `beam_file` (default: the
        simulation's), with `instr_params`; the wavelength must be the one of the beam file.
        Returns `output_dir/<time>_run_from_sample/mccode.h5` (or `folder_name/`). The number
        of neutrons is the number in the beam file."""
        output_path = run_folder(self.output_dir, folder_name, "run_from_sample")
        inst = self._build_from_sample(
            beam_file, output_path=str(output_path), force_compile=True, seed=seed
        )
        params = self._get_params(instr_params)
        inst.set_parameters(**params)
        inst.backengine()
        return output_path / "mccode.h5"

    def scan_from_sample(
        self,
        variable,
        values,
        folder_name=None,
        beam_file=None,
        n_jobs=None,
        seed=None,
        **instr_params,
    ):
        """Part 2 of a split run for every value of `variable` (e.g. "omega", range(-48, 83)),
        all starting from `beam_file` (default: the simulation's), the values in parallel
        (`n_jobs` single-process mcrun jobs at a time, default: all cores); the other instrument
        parameters are `instr_params`. Returns
        `output_dir/<time>_scan_<variable>_from_sample/mccode.h5` (or `folder_name/`), an entry per
        value. Each value gets its own random seed (`seed` + index), so the jobs do not repeat each
        other's random numbers."""
        points = self._points(variable, values, instr_params)  # checks `variable` names a parameter
        output_path = run_folder(self.output_dir, folder_name, f"scan_{variable}_from_sample")
        inst = self._build_from_sample(beam_file)
        return _run_points(inst, output_path, points, seed=seed, n_jobs=n_jobs)
