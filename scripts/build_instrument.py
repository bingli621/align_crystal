"""Build the McStas instrument of the single-crystal diffractometer (La2Ni7 sample), show it,
write its .instr file to mcstas_input/<instrument name>/, and simulate it (edit MODE: which `Simulation` method runs).

In VS Code: run this file, or from a notebook/Interactive Window:

    from build_instrument import create_instrument, create_mcstas, run_simulation
    scd = create_instrument()
    inst = create_mcstas(scd, plot=False)
    inst.show_diagram()
    run_simulation(scd, mode="scan")
"""

import numpy as np

from mcstas_to_sqe.instruments import Params, SingleCrystalDiffractometer
from mcstas_to_sqe.mcstas.builder import build_mcstas
from mcstas_to_sqe.mcstas.simulation import Simulation
from mcstas_to_sqe.samples import la2ni7


def create_instrument():
    """Return the single-crystal diffractometer with the La2Ni7 sample, printing the sample,
    the instrument, its parameters and its source."""
    # the sample, in the innermost goniometer arm
    sample = la2ni7(mosaic=60, at=[0, 0, 0], relative="gonio_phi")
    print(sample)

    scd = SingleCrystalDiffractometer(sample, Params(ei=14))
    print(scd)
    print(scd.params)
    print(scd.source)

    return scd


def create_mcstas(instrument, input_path=None, plot=True):
    """Return the McStasScript instrument of `instrument`, its .instr file written to
    `input_path` (None for mcstas_input/<instrument name>/). Print its parameters, components and instrument
    file, and with `plot` draw its diagram."""
    inst = build_mcstas(instrument, input_path=input_path)
    inst.write_full_instrument()  # show_instrument_file reads the file on disk: write it first
    inst.show_parameters()
    inst.show_components()
    inst.show_instrument_file(line_numbers=True)  # reads the file written above

    if plot:
        inst.show_diagram()

    return inst


# the `Simulation` method `run_simulation` runs: "run" | "scan" | "run_to_sample" (split part 1)
# | "run_from_sample" | "scan_from_sample" (split part 2, from the beam of part 1)
MODE = "scan"


def run_simulation(instrument, mode=MODE):
    """Simulate `instrument` (the diffractometer) with the `Simulation` method `mode`, printing
    the file it wrote."""
    sim = Simulation(instrument)
    if mode == "run":
        h5_file = sim.run(ncount=1e8, omega=30.0, chi=-5.893, phi=0.0)
    elif mode == "scan":
        h5_file = sim.scan("omega", np.linspace(-48, 83, 132), ncount=1e7, chi=-5.893, phi=0.0)
    elif mode == "run_to_sample":
        h5_file = sim.run_to_sample(ncount=1e8)
    elif mode == "run_from_sample":
        h5_file = sim.run_from_sample(omega=30.0, chi=-5.893, phi=0.0)
    elif mode == "scan_from_sample":
        h5_file = sim.scan_from_sample("omega", range(-48, 83), chi=-5.893, phi=0.0)
    else:
        raise ValueError(f"unknown mode {mode!r}")
    print(f"Wrote {h5_file}")


if __name__ == "__main__":
    scd = create_instrument()
    # create_mcstas(scd)
    run_simulation(scd)
