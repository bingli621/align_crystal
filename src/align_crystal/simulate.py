"""Run the diffractometer and write McStas NeXus (HDF5) output readable by mcstastox."""

import shutil
from pathlib import Path

from mcstasscript.helper.managed_mcrun import ManagedMcrun

from align_crystal.instrument import WORK_DIR, build_diffractometer


def run(
    output_path=WORK_DIR / "latest",
    ncount=1e7,
    sample=None,
    seed=None,
    mpi="auto",
    custom_flags=None,
    **angles,
):
    """Run a simulation; `angles` may contain omega, chi, phi (deg). Output goes to
    `output_path/mccode.h5`. `custom_flags` is passed to mcrun; with "-N 3" a
    parameter given as "min,max" (e.g. omega="3,5") is scanned over 3 points."""
    shutil.rmtree(output_path, ignore_errors=True)  # always start from a clean folder
    inst = build_diffractometer(sample=sample)
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
        inst.write_full_instrument()  # compiles in WORK_DIR
        params = {p.name: p.value for p in inst.parameters if p.name not in scans}
        options = dict(
            inst._run_settings, parameters=params | scans, output_path=inst.output_path
        )
        ManagedMcrun(inst.name + ".instr", **options).run_simulation()
    else:
        inst.backengine()  # compiles in WORK_DIR
    return Path(output_path) / "mccode.h5"


if __name__ == "__main__":
    # Edit the settings below and run this file (e.g. with VS Code's ▶ button).
    from align_crystal.samples import la2ni7

    h5_file = run(
        ncount=1e6,
        sample=la2ni7(mosaic=60),
        omega="-48,73",  # scan omega
        chi=-5.893,
        phi=0.0,
        custom_flags="-N 122",
    )
    print(f"Wrote {h5_file}")
