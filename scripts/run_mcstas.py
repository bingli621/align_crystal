"""Simulate the single-crystal diffractometer (La2Ni7 sample) of build_instrument.py (edit MODE:
which `Simulation` method runs), writing into a new run folder of mcstas_output/.

In VS Code: run this file, or from a notebook/Interactive Window:

    from build_instrument import create_instrument
    from run_mcstas import run_simulation
    scd = create_instrument()
    run_simulation(scd, mode="scan")
"""

import numpy as np
from build_instrument import create_instrument

from mcstas_to_sqe.mcstas.run_folders import clean_runs  # noqa: F401 (see __main__)
from mcstas_to_sqe.mcstas.simulation import Simulation

# the `Simulation` method `run_simulation` runs: "run" | "scan" | "run_to_sample" (split part 1)
# | "run_from_sample" | "scan_from_sample" (split part 2, from the beam of part 1)
MODE = "scan_from_sample"


def run_simulation(instrument, mode=MODE):
    """Simulate `instrument` (the diffractometer) with the `Simulation` method `mode`, printing
    and returning the file it wrote."""
    sim = Simulation(instrument)
    if mode == "run":
        h5_file = sim.run(ncount=1e6, omega=30.0, chi=-5.893, phi=0.0)
    elif mode == "scan":
        h5_file = sim.scan("omega", np.linspace(-48, 83, 132), ncount=1e7, chi=-5.893, phi=0.0)
    elif mode == "run_to_sample":
        h5_file = sim.run_to_sample(ncount=1e7)
    elif mode == "run_from_sample":
        h5_file = sim.run_from_sample(omega=30.0, chi=-5.893, phi=0.0)
    elif mode == "scan_from_sample":
        h5_file = sim.scan_from_sample("omega", range(-48, 83), chi=-5.893, phi=0.0)
    else:
        raise ValueError(f"unknown mode {mode!r}")
    print(f"Wrote {h5_file}")
    return h5_file


if __name__ == "__main__":
    scd = create_instrument()
    run_simulation(scd)
    # clean_runs(keep=5)  # remove all but the 5 newest runs (never a run_to_sample run)
