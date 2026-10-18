"""Make the small split run in tests/data/split_run/ that the reduction tests read.

A beam run (`dump_beam`) and a run from its beam at two omegas (`run_from_beam`) of La2Ni7 at
14 meV. Only the two `mccode.h5` files are kept, their large datasets compressed (h5repack).
Rerun it (`pixi run python tests/data/make_split_run.py`) if McStas output changes in a way the
tests should follow.
"""

import shutil
import subprocess
from pathlib import Path

from align_crystal.instrument import SingleCrystalDiffractometer, la2ni7
from align_crystal.mcstas.simulater import dump_beam, run_from_beam

HERE = Path(__file__).parent / "split_run"
CRYSTAL = {"mosaic": 60, "at": [0, 0, 0], "relative": "gonio_phi"}

if __name__ == "__main__":
    work = HERE.parent / "_split_run_work"
    shutil.rmtree(work, ignore_errors=True)
    diffractometer = SingleCrystalDiffractometer(la2ni7(**CRYSTAL), ei=14)
    beam = dump_beam(output_path=work / "beam", ncount=2e4, config=diffractometer)
    run_from_beam(
        omegas=[-5, 5],
        beam_file=beam,
        output_path=work / "split",
        config=diffractometer,
        chi=-5.893,
        phi=0.0,
        n_jobs=2,
        seed=1,
    )
    shutil.rmtree(HERE, ignore_errors=True)
    for run in ("beam", "split"):
        (HERE / run).mkdir(parents=True)
        # gzip the large datasets (the detector pixels), not the many small ones
        subprocess.run(
            [
                "h5repack",
                "-m",
                "65536",
                "-f",
                "GZIP=9",
                work / run / "mccode.h5",
                HERE / run / "mccode.h5",
            ],
            check=True,
        )
    shutil.rmtree(work)
    print(f"Wrote {sorted(str(p.relative_to(HERE)) for p in HERE.rglob('*.h5'))}")
