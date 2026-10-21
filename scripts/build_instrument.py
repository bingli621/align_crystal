"""Build the McStas instrument of the single-crystal diffractometer (La2Ni7 sample), show it,
and write its .instr file to mcstas_input/.

In VS Code: run this file, or from a notebook/Interactive Window:

    from build_instrument import build_instrument
    inst = build_instrument()
    inst.show_diagram()
"""

from align_crystal.instruments import SingleCrystalDiffractometer
from align_crystal.mcstas.builder import build_mcstas
from align_crystal.samples import la2ni7


def build_instrument(input_path=None, plot=True):
    """Return the McStasScript instrument, its .instr file written to `input_path` (None for
    mcstas_input/). Print its parameters, components and instrument file, and with `plot`
    draw its diagram."""
    # the sample, in the innermost goniometer arm
    sample = la2ni7(at=[0, 0, 0], relative="gonio_phi")
    print(sample)

    scd = SingleCrystalDiffractometer(sample)
    print(scd)
    print(scd.params)
    print(scd.source)

    inst = build_mcstas(scd, input_path=input_path)
    inst.write_full_instrument()  # show_instrument_file reads the file on disk: write it first
    inst.show_parameters()
    inst.show_components()
    inst.show_instrument_file(line_numbers=True)  # reads the file written above

    if plot:
        inst.show_diagram()

    return inst


if __name__ == "__main__":
    build_instrument()
