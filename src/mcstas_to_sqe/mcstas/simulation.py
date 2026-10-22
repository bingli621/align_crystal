"""Simulate an instrument into McStas NeXus (HDF5) output, read with `nexus_io.read_scan`.

A `Simulation` holds the instrument to simulate and the folder its runs write to:

- `run`: one run, source -> detector;
- `scan`: a run per value of an instrument parameter, source -> detector, the values in parallel;
- `run_to_sample`: source -> `sample_pos` once, the beam dumped into an MCPL beam file;
- `run_from_sample`: one run from that beam file, `sample_pos` -> detector;
- `scan_from_sample`: a run per value from that beam file, the values in parallel.

Everything runs through McStasScript's public API (`settings`, `set_parameters`, `run_to`,
`run_from`, `backengine`); a scan is a `backengine` per value, merged into one file, after
compiling the instrument once with mcrun itself (McStasScript has no compile-only call).
"""

import copy
import os
import shlex
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np

from mcstas_to_sqe.mcstas.builder import build_mcstas, default_input_dir
from mcstas_to_sqe.mcstas.nexus_io import merge_entries
from mcstas_to_sqe.mcstas.run_folders import default_output_dir, latest_beam, run_folder


def _compile(inst):
    """Write `inst` into its input folder and compile it there, without simulating: mcrun
    compiles (-c), then the instrument only prints its info (--info), so not even a beam file
    is read. The compile flags are the ones of `inst`'s settings (NeXus, OpenACC, custom flags),
    so its runs reuse the executable. Raises RuntimeError with mcrun's output if that fails."""
    inst.write_full_instrument()
    options = inst._run_settings  # McStasScript keeps them private
    mcrun = Path(options.get("executable_path", "")) / options.get("executable", "mcrun")
    command = [str(mcrun), "-c", "--info"]
    if options.get("NeXus"):
        command.append("--format=NeXus")
    if options.get("openacc"):
        command.append("--openacc")
    command += [*shlex.split(options.get("custom_flags", "")), f"{inst.name}.instr"]
    process = subprocess.run(
        command, cwd=inst.input_path, capture_output=True, text=True, check=False
    )
    if process.returncode != 0:
        raise RuntimeError(f"compiling {inst.name} failed:\n{process.stdout}{process.stderr}")


def _run_points_in_parallel(inst, output_path, points, seed=None, n_jobs: int | None = None):
    """Run `inst` once per point (instrument parameter values, McStas name -> value), `n_jobs`
    at a time (None: all cores), and merge the outputs into `output_path/mccode.h5`, an entry
    per point in the order of `points`, which is returned.

    Each point runs a copy of `inst`, with its own values, output folder and random seed (`seed`
    + index, default: a random `seed`), so the runs do not repeat each other's random numbers.
    The instrument is written and compiled once, first, without simulating; then every point
    reuses it, in parallel.

    A point that fails raises RuntimeError naming it, once the points already running are done;
    the points not started yet are not run, and the folder of every point is kept in
    `output_path`. Raises ValueError, before anything, if there are no points.
    """
    if not points:
        raise ValueError("a scan needs at least one point")
    _compile(inst)  # once, before any point
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
            force_compile=False,  # compiled once, above
        )
        run.set_parameters(**values)
        runs.append(run)

    def run_point(n):
        try:
            runs[n].backengine()  # a separate mcrun process
        except Exception as error:
            raise RuntimeError(f"point {n} {points[n]} failed, see {folders[n]}") from error

    with ThreadPoolExecutor(max_workers=n_jobs or os.cpu_count()) as pool:
        futures = [pool.submit(run_point, n) for n in range(len(runs))]
        for future in as_completed(futures):
            if future.exception() is not None:
                pool.shutdown(wait=False, cancel_futures=True)  # the exit waits for the running
                future.result()

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

    def _sample_pos_name(self):
        """The name of the instrument's `sample_pos`, where a split run cuts the beam; an
        instrument without one raises."""
        sample_pos = getattr(self.instrument, "sample_pos", None)
        if sample_pos is None or sample_pos.name not in self.instrument.components:
            raise ValueError(
                f"{self.instrument.name} has no sample_pos component to split a run at"
            )
        return sample_pos.name

    def find_beam_file(self, beam_file=None):
        """The absolute path of the beam file a run from the sample starts from: `beam_file`,
        or None for the simulation's (`self.beam_file`). Absolute, as mcrun runs in `input_dir`.

        Raises FileNotFoundError if both are None."""
        beam_file = beam_file or self.beam_file
        if beam_file is None:
            raise FileNotFoundError(f"no beam file in {self.output_dir}: run run_to_sample first")
        return Path(beam_file).resolve()

    def get_scan_points(self, variable, values, instr_params):
        """The points of a scan of `variable` over `values`, one `{**instr_params, variable: value}`
        each. Every name is checked against the instrument's parameters (KeyError), before any
        run."""
        names = {p.name for p in self.instrument.instr_params}
        if unknown := sorted({variable, *instr_params} - names):
            raise KeyError(f"no instrument parameter {unknown}, only {sorted(names)}")
        return [
            {**instr_params, variable: value} for value in np.asarray(values, dtype=float).tolist()
        ]

    def run(
        self, folder_name=None, ncount=1e7, seed=None, mpi="auto", custom_flags=None, **instr_params
    ):
        """Run source -> detector once, with `instr_params`. Output goes to
        `output_dir/<time>_run/mccode.h5` (or `folder_name/`), which is returned. `custom_flags`
        is passed to mcrun."""
        output_path = run_folder(self.output_dir, folder_name, "run")
        inst = build_mcstas(self.instrument, input_path=self.input_dir)
        inst.settings(
            NeXus=True,
            increment_folder_name=False,
            suppress_output=True,
            output_path=str(output_path),
            ncount=ncount,
            mpi=mpi,
            force_compile=True,
            seed=seed,
            custom_flags=custom_flags,
        )
        inst.set_parameters(**instr_params)  # the rest keep the instrument's values
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
        points = self.get_scan_points(variable, values, instr_params)  # checked before anything
        output_path = run_folder(self.output_dir, folder_name, f"scan_{variable}")
        inst = build_mcstas(self.instrument, input_path=self.input_dir)
        inst.settings(
            NeXus=True,
            increment_folder_name=False,
            suppress_output=True,
            ncount=ncount,
            # no MPI (None, though McStasScript hints str): the points run in parallel instead
            mpi=None,  # pyright: ignore[reportArgumentType]
            custom_flags=custom_flags,
        )

        return _run_points_in_parallel(inst, output_path, points, seed=seed, n_jobs=n_jobs)

    def run_to_sample(self, folder_name=None, ncount=1e8, mpi="auto", **instr_params):
        """Part 1 of a split run: simulate source -> slit -> incident monitor -> `sample_pos` and
        dump the beam to an MCPL file. Run it once with a large `ncount`. Returns the path of the
        beam file (`output_dir/<time>_run_to_sample/beam.mcpl.gz`, or `folder_name/`), which becomes
        `beam_file`; the folder also has `mccode.h5` with the incident monitor.

        The beam file only fits instruments with the same source and beam geometry, and the same
        wavelength, so make a new one if you change the instrument's ei, source, slit or monitor
        settings.
        """
        sample_pos = self._sample_pos_name()  # checked before anything
        output_path = run_folder(self.output_dir, folder_name, "run_to_sample")
        inst = build_mcstas(self.instrument, input_path=self.input_dir)
        inst.settings(
            NeXus=True,
            increment_folder_name=False,
            suppress_output=True,
            output_path=str(output_path),
            ncount=ncount,
            mpi=mpi,
            force_compile=True,
        )
        inst.set_parameters(**instr_params)  # the rest keep the instrument's values
        inst.run_to(
            sample_pos,
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
        sample_pos = self._sample_pos_name()  # checked before anything
        beam_file = self.find_beam_file(beam_file)
        output_path = run_folder(self.output_dir, folder_name, "run_from_sample")
        inst = build_mcstas(self.instrument, input_path=self.input_dir)
        inst.settings(
            NeXus=True,
            increment_folder_name=False,
            suppress_output=True,
            output_path=str(output_path),
            # no MPI (None, though McStasScript hints str): the ranks would repeat the beam file
            mpi=None,  # pyright: ignore[reportArgumentType]
            force_compile=True,
            seed=seed,
        )
        inst.run_from(sample_pos, filename=f'"{beam_file}"')
        inst.set_parameters(**instr_params)  # the rest keep the instrument's values
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
        points = self.get_scan_points(variable, values, instr_params)  # checked before anything
        sample_pos = self._sample_pos_name()
        beam_file = self.find_beam_file(beam_file)
        inst = build_mcstas(self.instrument, input_path=self.input_dir)
        inst.settings(
            NeXus=True,
            increment_folder_name=False,
            suppress_output=True,
            # no MPI (None, though McStasScript hints str): the ranks would repeat the beam file
            mpi=None,  # pyright: ignore[reportArgumentType]
        )
        inst.run_from(sample_pos, filename=f'"{beam_file}"')
        output_path = run_folder(self.output_dir, folder_name, f"scan_{variable}_from_sample")
        return _run_points_in_parallel(inst, output_path, points, seed=seed, n_jobs=n_jobs)
