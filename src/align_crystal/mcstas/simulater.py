"""Run the diffractometer and write McStas NeXus (HDF5) output readable by mcstastox."""

import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import h5py
import numpy as np
from mcstasscript.helper.managed_mcrun import ManagedMcrun

from align_crystal.file_io import load_config
from align_crystal.mcstas.builder import OUTPUT_DIR, build_instrument


def _run_scan(inst, scans):
    """Run `inst` with mcrun scan ranges, e.g. {"omega": "3,5"} together with custom_flags "-N 3".
    McStasScript's parameters only take numbers, so the ranges are given to mcrun directly."""
    inst.write_full_instrument()  # compiles in OUTPUT_DIR
    params = {p.name: p.value for p in inst.parameters if p.name not in scans}
    options = dict(
        inst._run_settings, parameters=params | scans, output_path=inst.output_path
    )
    ManagedMcrun(inst.name + ".instr", **options).run_simulation()


def run(
    output_path=OUTPUT_DIR / "latest",
    ncount=1e7,
    sample=None,
    config=None,
    seed=None,
    mpi="auto",
    custom_flags=None,
    **angles,
):
    """Run a simulation; `config` is anything `load_config` takes (default: the default config).
    `angles` may contain omega, chi, phi (deg). Output goes to
    `output_path/mccode.h5`. `custom_flags` is passed to mcrun; with "-N 3" a
    parameter given as "min,max" (e.g. omega="3,5") is scanned over 3 points."""
    shutil.rmtree(output_path, ignore_errors=True)  # always start from a clean folder
    inst = build_instrument(load_config(config), sample=sample)
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
    # a "min,max" string is an mcrun scan range; McStasScript's parameters only take numbers
    scans = {k: v for k, v in angles.items() if isinstance(v, str)}
    inst.set_parameters(**{k: v for k, v in angles.items() if k not in scans})
    if scans:
        _run_scan(inst, scans)
    else:
        inst.backengine()  # compiles in OUTPUT_DIR
    return Path(output_path) / "mccode.h5"


def dump_beam(output_path=OUTPUT_DIR / "beam", ncount=1e8, mpi="auto", config=None):
    """Part 1 of a split run: simulate source -> slit -> incident monitor -> `sample_pos` and dump
    the beam to an MCPL file. Run it once with a large `ncount`. Returns the path of the beam file
    (`<output_path>/beam.mcpl.gz`); the folder also has `mccode.h5` with the incident monitor.

    The beam file only fits instruments with the same source and beam geometry, so make a new
    one if you change the config's source, slit or monitor settings.
    """
    output_path = Path(output_path)
    shutil.rmtree(output_path, ignore_errors=True)
    output_path.parent.mkdir(
        parents=True, exist_ok=True
    )  # mcrun does not create parent folders
    inst = build_instrument(load_config(config))
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
    sample=None,
    config=None,
    chi=0.0,
    phi=0.0,
    n_jobs=None,
    seed=None,
):
    """Part 2 of a split run, can be done any time later (even in another session): simulate
    `sample_pos` -> crystal -> detector for every omega, all starting from the same beam file made
    by `dump_beam`, with the angles running in parallel (`n_jobs` single-process mcrun jobs at a
    time, default: all cores). Returns the path of `<output_path>/mccode.h5`, one file with an
    entry per omega (`entry1`, `entry2`, ... in the order of `omegas`).

    The number of neutrons is the number in the beam file (`ncount` is ignored). Each angle is
    run in a single process, with MPI the ranks would all repeat the same neutrons. Each angle gets
    its own random seed (`seed` + index), so the jobs do not repeat each other's random numbers.
    """
    beam_file = Path(beam_file).resolve()
    if not beam_file.exists():
        raise FileNotFoundError(f"{beam_file} not found, run dump_beam first.")
    output_path = Path(output_path)
    shutil.rmtree(output_path, ignore_errors=True)
    output_path.mkdir(parents=True)  # mcrun does not create missing parent folders
    omegas = list(omegas)
    seed = (
        int(np.random.SeedSequence().generate_state(1)[0] % 10**9)
        if seed is None
        else seed
    )

    inst = build_instrument(load_config(config), sample=sample)
    inst.run_from("sample_pos", filename=f'"{beam_file}"')
    inst.settings(
        output_path=str(output_path),
        mpi=None,
        NeXus=True,
        increment_folder_name=False,
        suppress_output=True,
    )
    inst.write_full_instrument()  # the instrument is the same for every angle

    # one mcrun job per angle: own parameters, output folder and seed
    jobs = []
    for n, omega in enumerate(omegas):
        inst.set_parameters(omega=omega, chi=chi, phi=phi)
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
    from align_crystal.samples import la2ni7

    MODE = "from_beam"  # "full": one run | "dump": split part 1 | "from_beam": split part 2

    if MODE == "full":
        h5_file = run(
            ncount=1e6,
            sample=la2ni7(mosaic=60),
            omega="-48,73",  # scan omega
            chi=-5.893,
            phi=0.0,
            custom_flags="-N 122",
        )
        print(f"Wrote {h5_file}")
    elif MODE == "dump":
        print(f"Wrote {dump_beam(ncount=1e8)}")
    elif MODE == "from_beam":
        h5_file = run_from_beam(
            omegas=range(-48, 74), sample=la2ni7(mosaic=60), chi=-5.893, phi=0.0
        )
        print(f"Wrote {h5_file}")
