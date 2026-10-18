"""Run the diffractometer and write McStas NeXus (HDF5) output readable by mcstastox."""

import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import h5py
import numpy as np
from mcstasscript.helper.managed_mcrun import ManagedMcrun

from align_crystal.mcstas.builder import OUTPUT_DIR, build_instrument


def _set_instr_params(inst, config, instr_params):
    """Set the instrument parameters of a run on `inst`: those of `config`, with `instr_params`
    (McStas name -> value) in place of the diffractometer's. A "min,max" string is an mcrun scan
    range: it is returned, not set, since McStasScript's parameters only take numbers."""
    values = {p.name: p.value for p in config.instr_params} | instr_params
    scans = {k: v for k, v in values.items() if isinstance(v, str)}
    inst.set_parameters(**{k: v for k, v in values.items() if k not in scans})
    return scans


def _run_scan(inst, scans):
    """Run `inst` with mcrun scan ranges, e.g. {"omega": "3,5"} together with custom_flags "-N 3".
    McStasScript's parameters only take numbers, so the ranges are given to mcrun directly."""
    inst.write_full_instrument()  # compiles in OUTPUT_DIR
    params = {p.name: p.value for p in inst.parameters if p.name not in scans}
    options = dict(inst._run_settings, parameters=params | scans, output_path=inst.output_path)
    ManagedMcrun(inst.name + ".instr", **options).run_simulation()


def run(
    output_path=OUTPUT_DIR / "latest",
    ncount=1e7,
    config=None,
    seed=None,
    mpi="auto",
    custom_flags=None,
    **instr_params,
):
    """Run a simulation; `config` is the `SingleCrystalDiffractometer` to simulate. `instr_params` are
    its instrument parameters for this run, by McStas name: omega, chi, phi (deg; the diffractometer's unless given). The
    `wavelength` (angstrom) is one of them: the one of the diffractometer's ei unless the run gives
    it. Output goes to `output_path/mccode.h5`. `custom_flags` is passed to
    mcrun; with "-N 3" an instrument parameter given as "min,max" (e.g. omega="3,5") is scanned over 3 points."""
    shutil.rmtree(output_path, ignore_errors=True)  # always start from a clean folder
    inst = build_instrument(config)
    inst.settings(
        output_path=str(output_path),
        ncount=ncount,
        mpi=mpi,
        NeXus=True,
        increment_folder_name=False,
        force_compile=True,
        seed=seed,
        suppress_output=True,
        custom_flags=custom_flags,
    )
    scans = _set_instr_params(inst, config, instr_params)
    if scans:
        _run_scan(inst, scans)
    else:
        inst.backengine()  # compiles in OUTPUT_DIR
    return Path(output_path) / "mccode.h5"


def dump_beam(output_path=OUTPUT_DIR / "beam", ncount=1e8, mpi="auto", config=None, **instr_params):
    """Part 1 of a split run: simulate source -> slit -> incident monitor -> `sample_pos` and dump
    the beam to an MCPL file. Run it once with a large `ncount`. Returns the path of the beam file
    (`<output_path>/beam.mcpl.gz`); the folder also has `mccode.h5` with the incident monitor.
    `instr_params` are the instrument parameters of the run (no scan ranges), in place of the
    diffractometer's.

    The beam file only fits instruments with the same source and beam geometry, and the same
    wavelength, so make a new one if you change the config's ei, source, slit or monitor
    settings.
    """
    output_path = Path(output_path)
    shutil.rmtree(output_path, ignore_errors=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)  # mcrun does not create parent folders
    inst = build_instrument(config)
    _set_instr_params(inst, config, instr_params)
    inst.settings(
        output_path=str(output_path),
        ncount=ncount,
        mpi=mpi,
        NeXus=True,
        increment_folder_name=False,
        force_compile=True,
        suppress_output=True,
    )
    inst.run_to(
        "sample_pos",
        run_name="beam",
        comment=f"{ncount:g} neutrons",
        filename='"beam.mcpl"',
    )
    inst.backengine()
    return output_path / "beam.mcpl.gz"


def run_from_beam(
    omegas,
    beam_file=OUTPUT_DIR / "beam" / "beam.mcpl.gz",
    output_path=OUTPUT_DIR / "split",
    config=None,
    n_jobs=None,
    seed=None,
    **instr_params,
):
    """Part 2 of a split run, can be done any time later (even in another session): simulate
    `sample_pos` -> sample -> detector for every omega, all starting from the same beam file made
    by `dump_beam`, with the angles running in parallel (`n_jobs` single-process mcrun jobs at a
    time, default: all cores). `instr_params` are the other instrument parameters, the same for every
    omega: chi, phi (deg; the diffractometer's unless given); the wavelength must be the one of the beam file. Returns
    the path of `<output_path>/mccode.h5`, one file with an entry per omega (`entry1`, `entry2`,
    ... in the order of `omegas`).

    The number of neutrons is the number in the beam file (`ncount` is ignored). Each angle is
    run in a single process, with MPI the ranks would all repeat the same neutrons. Each angle gets
    its own random seed (`seed` + index), so the jobs do not repeat each other's random numbers.
    """
    beam_file = Path(beam_file).resolve()
    output_path = Path(output_path)
    shutil.rmtree(output_path, ignore_errors=True)
    output_path.mkdir(parents=True)  # mcrun does not create missing parent folders
    omegas = list(omegas)
    seed = int(np.random.SeedSequence().generate_state(1)[0] % 10**9) if seed is None else seed

    inst = build_instrument(config)
    inst.run_from("sample_pos", filename=f'"{beam_file}"')
    inst.settings(
        output_path=str(output_path),
        mpi=None,
        NeXus=True,
        increment_folder_name=False,
        suppress_output=True,
    )
    # the instrument is the same for every angle; its parameters are written with the values of the
    # first one as defaults: McStas only records a parameter that has a default in the output
    _set_instr_params(inst, config, {**instr_params, "omega": omegas[0]})
    inst.write_full_instrument()

    # one mcrun job per angle: own parameters, output folder and seed
    jobs = []
    for n, omega in enumerate(omegas):
        _set_instr_params(inst, config, {**instr_params, "omega": omega})
        jobs.append(
            dict(
                inst._run_settings,
                parameters={p.name: p.value for p in inst.parameters},
                output_path=str(output_path / f"omega_{n:04d}"),
                seed=seed + n + 1,  # mcrun does not accept seed 0
                force_compile=(n == 0),
            )
        )

    def run_job(job):
        ManagedMcrun(inst.name + ".instr", **job).run_simulation()

    run_job(jobs[0])  # compile once, on the first angle
    with ThreadPoolExecutor(max_workers=n_jobs or os.cpu_count()) as pool:
        list(pool.map(run_job, jobs[1:]))  # each job is a separate mcrun process

    # merge the single-entry files into one file with an entry per omega, then remove the folders
    merged = output_path / "mccode.h5"
    with h5py.File(merged, "w") as out:
        for n in range(len(omegas)):
            folder = output_path / f"omega_{n:04d}"
            with h5py.File(folder / "mccode.h5") as part:
                part.copy(part["entry1"], out, name=f"entry{n + 1}")
            shutil.rmtree(folder)
    return merged


if __name__ == "__main__":
    # Edit the settings below and run this file (e.g. with VS Code's ▶ button).
    from align_crystal.instrument import SingleCrystalDiffractometer, la2ni7

    # the sample, in the innermost goniometer arm; ei: incident energy, meV
    sample = la2ni7(mosaic=60, at=[0, 0, 0], relative="gonio_phi")
    diffractometer = SingleCrystalDiffractometer(sample, ei=14)
    MODE = "from_beam"  # "full": one run | "dump": split part 1 | "from_beam": split part 2

    if MODE == "full":
        h5_file = run(
            config=diffractometer,
            ncount=1e6,
            omega="-48,73",  # scan omega
            chi=-5.893,
            phi=0.0,
            custom_flags="-N 122",
        )
        print(f"Wrote {h5_file}")
    elif MODE == "dump":
        print(f"Wrote {dump_beam(ncount=1e8, config=diffractometer)}")
    elif MODE == "from_beam":
        h5_file = run_from_beam(
            omegas=range(-48, 74),
            config=diffractometer,
            chi=-5.893,
            phi=0.0,
        )
        print(f"Wrote {h5_file}")
