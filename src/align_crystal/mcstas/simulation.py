"""Simulate an instrument and read its McStas NeXus (HDF5) output, readable by mcstastox.

A `Simulation` holds the instrument to simulate and the folder its runs write to:

- `run`: one run, source -> detector, optionally an mcrun scan of an instrument parameter;
- `dump_beam` and `run_from_beam`: a split run, source -> `sample_pos` once into an MCPL beam
  file, then `sample_pos` -> detector for many omegas in parallel from that beam file;
- `read`: the output of the last run (or of any folder), with `h5_reader.read_scan`.
"""

import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import h5py
import numpy as np
from mcstasscript.helper.managed_mcrun import ManagedMcrun

from align_crystal.mcstas.builder import OUTPUT_DIR, build
from align_crystal.mcstas.h5_reader import read_scan


def _clean_folder(path):
    """Remove `path`, so a run starts from a clean folder, and create its parent folders: mcrun
    does not create them."""
    path = Path(path)
    shutil.rmtree(path, ignore_errors=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _mcrun(inst, **options):
    """Run the written instrument `inst` with mcrun: its run settings, with `options` in place."""
    ManagedMcrun(inst.name + ".instr", **(inst._run_settings | options)).run_simulation()


def _run_scan(inst, scans):
    """Run `inst` with mcrun scan ranges, e.g. {"omega": "3,5"} together with custom_flags "-N 3".
    McStasScript's parameters only take numbers, so the ranges are given to mcrun directly."""
    inst.write_full_instrument()  # compiles in OUTPUT_DIR
    params = {p.name: p.value for p in inst.parameters if p.name not in scans}
    _mcrun(inst, parameters=params | scans, output_path=inst.output_path)


def _merge_entries(folders, merged):
    """Write the single-entry `mccode.h5` of each of `folders` into one file `merged`, as
    `entry1`, `entry2`, ... in the order of `folders`, and remove the folders."""
    with h5py.File(merged, "w") as out:
        for n, folder in enumerate(folders, start=1):
            with h5py.File(folder / "mccode.h5") as part:
                part.copy(part["entry1"], out, name=f"entry{n}")
            shutil.rmtree(folder)
    return merged


class Simulation:
    """Runs of `instrument` (e.g. a `SingleCrystalDiffractometer`), each into a folder of
    `output_dir`: `latest/` for `run`, `beam/` for `dump_beam`, `split/` for `run_from_beam`
    (`name` gives another one). Every run builds the instrument anew, so a change to it applies
    to the next run.

    `beam_file` is the beam file `run_from_beam` starts from: the one of the last `dump_beam`,
    else `output_dir/beam/beam.mcpl.gz`, so a beam dumped in an earlier session is found.
    `last_output` is the folder of the last run, which `read` reads.
    """

    def __init__(self, instrument, output_dir=OUTPUT_DIR):
        self.instrument = instrument
        self.output_dir = Path(output_dir)
        self.beam_file = self.output_dir / "beam" / "beam.mcpl.gz"
        self.last_output = None

    def _build(self, output_path, **settings):
        """Return the McStasScript instrument, with NeXus output into `output_path` and the
        other run `settings`."""
        inst = build(self.instrument)
        inst.settings(
            output_path=str(output_path),
            NeXus=True,
            increment_folder_name=False,
            suppress_output=True,
            **settings,
        )
        return inst

    def _set_instr_params(self, inst, instr_params):
        """Set the instrument parameters of a run on `inst`: the instrument's, with `instr_params`
        (McStas name -> value) in place. A "min,max" string is an mcrun scan range: it is returned,
        not set, since McStasScript's parameters only take numbers."""
        values = {p.name: p.value for p in self.instrument.instr_params} | instr_params
        scans = {k: v for k, v in values.items() if isinstance(v, str)}
        inst.set_parameters(**{k: v for k, v in values.items() if k not in scans})
        return scans

    def _start(self, name):
        """The clean output folder `name` of a run, remembered as the last output."""
        self.last_output = _clean_folder(self.output_dir / name)
        return self.last_output

    def run(
        self, name="latest", ncount=1e7, seed=None, mpi="auto", custom_flags=None, **instr_params
    ):
        """Run a simulation. `instr_params` are the instrument parameters for this run, by McStas
        name: omega, chi, phi (deg; the instrument's unless given). The `wavelength` (angstrom) is
        one of them: the one of the instrument's ei unless the run gives it. Output goes to
        `output_dir/name/mccode.h5`, which is returned. `custom_flags` is passed to mcrun; with
        "-N 3" an instrument parameter given as "min,max" (e.g. omega="3,5") is scanned over 3
        points."""
        output_path = self._start(name)
        inst = self._build(
            output_path,
            ncount=ncount,
            mpi=mpi,
            force_compile=True,
            seed=seed,
            custom_flags=custom_flags,
        )
        if scans := self._set_instr_params(inst, instr_params):
            _run_scan(inst, scans)
        else:
            inst.backengine()  # compiles in OUTPUT_DIR
        return output_path / "mccode.h5"

    def dump_beam(self, name="beam", ncount=1e8, mpi="auto", **instr_params):
        """Part 1 of a split run: simulate source -> slit -> incident monitor -> `sample_pos` and
        dump the beam to an MCPL file. Run it once with a large `ncount`. Returns the path of the
        beam file (`output_dir/name/beam.mcpl.gz`), which becomes `beam_file`; the folder also has
        `mccode.h5` with the incident monitor. `instr_params` are the instrument parameters of the
        run (no scan ranges), in place of the instrument's.

        The beam file only fits instruments with the same source and beam geometry, and the same
        wavelength, so make a new one if you change the instrument's ei, source, slit or monitor
        settings.
        """
        output_path = self._start(name)
        inst = self._build(output_path, ncount=ncount, mpi=mpi, force_compile=True)
        self._set_instr_params(inst, instr_params)
        inst.run_to(
            self.instrument.sample_pos.name,
            run_name="beam",
            comment=f"{ncount:g} neutrons",
            filename='"beam.mcpl"',
        )
        inst.backengine()
        self.beam_file = output_path / "beam.mcpl.gz"
        return self.beam_file

    def run_from_beam(
        self, omegas, name="split", beam_file=None, n_jobs=None, seed=None, **instr_params
    ):
        """Part 2 of a split run, can be done any time later (even in another session): simulate
        `sample_pos` -> sample -> detector for every omega, all starting from the same beam file
        (`beam_file`, default: the simulation's), with the angles running in parallel (`n_jobs`
        single-process mcrun jobs at a time, default: all cores). `instr_params` are the other
        instrument parameters, the same for every omega: chi, phi (deg; the instrument's unless
        given); the wavelength must be the one of the beam file. Returns the path of
        `output_dir/name/mccode.h5`, one file with an entry per omega (`entry1`, `entry2`, ... in
        the order of `omegas`).

        The number of neutrons is the number in the beam file (`ncount` is ignored). Each angle
        is run in a single process, with MPI the ranks would all repeat the same neutrons. Each
        angle gets its own random seed (`seed` + index), so the jobs do not repeat each other's
        random numbers.
        """
        beam_file = Path(beam_file or self.beam_file).resolve()
        output_path = self._start(name)
        output_path.mkdir()  # holds a folder per angle
        omegas = list(omegas)
        if seed is None:
            seed = int(np.random.SeedSequence().generate_state(1)[0] % 10**9)

        inst = self._build(output_path, mpi=None)
        inst.run_from(self.instrument.sample_pos.name, filename=f'"{beam_file}"')
        # the instrument is the same for every angle; its parameters are written with the values
        # of the first one as defaults: McStas only records a parameter that has a default in the
        # output
        self._set_instr_params(inst, {**instr_params, "omega": omegas[0]})
        inst.write_full_instrument()

        # one mcrun job per angle: own parameters, output folder and seed
        folders = [output_path / f"omega_{n:04d}" for n in range(len(omegas))]
        jobs = []
        for n, (omega, folder) in enumerate(zip(omegas, folders)):
            self._set_instr_params(inst, {**instr_params, "omega": omega})
            jobs.append(
                {
                    "parameters": {p.name: p.value for p in inst.parameters},
                    "output_path": str(folder),
                    "seed": seed + n + 1,  # mcrun does not accept seed 0
                    "force_compile": n == 0,
                }
            )

        def run_job(job):
            _mcrun(inst, **job)

        run_job(jobs[0])  # compile once, on the first angle
        with ThreadPoolExecutor(max_workers=n_jobs or os.cpu_count()) as pool:
            list(pool.map(run_job, jobs[1:]))  # each job is a separate mcrun process

        return _merge_entries(folders, output_path / "mccode.h5")

    def read(self, folder=None, **kwargs):
        """Return `read_scan` of `folder` (default: the last run's), a (parameters, events) per
        scan point; `kwargs` go to `read_scan` (e.g. `component`)."""
        folder = folder or self.last_output
        if folder is None:
            raise ValueError("nothing to read: no run yet, give the folder")
        return read_scan(folder, **kwargs)


if __name__ == "__main__":
    # Edit the settings below and run this file (e.g. with VS Code's ▶ button).
    from align_crystal.instruments import Params, SingleCrystalDiffractometer
    from align_crystal.samples import la2ni7

    # the sample, in the innermost goniometer arm; ei: incident energy, meV
    sample = la2ni7(mosaic=60, at=[0, 0, 0], relative="gonio_phi")
    sim = Simulation(SingleCrystalDiffractometer(sample, Params(ei=14)))
    MODE = "dump"  # "full": one run | "dump": split part 1 | "from_beam": split part 2

    if MODE == "full":
        h5_file = sim.run(
            ncount=1e6,
            omega="-48,83",  # scan omega
            chi=-5.893,
            phi=0.0,
            custom_flags="-N 11",
        )
    elif MODE == "dump":
        h5_file = sim.dump_beam(ncount=1e8)
    elif MODE == "from_beam":
        h5_file = sim.run_from_beam(omegas=range(-48, 83), chi=-5.893, phi=0.0)
    else:
        raise ValueError(f"unknown MODE {MODE!r}")
    print(f"Wrote {h5_file}")
