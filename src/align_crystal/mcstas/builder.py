"""Build the McStas instrument (McStasScript) of any `Instrument`.

Its instrument parameters, then its components one by one, in the order of the beam (McStas
positions are relative to earlier ones). Each is added as its `component_name`, named its `name`,
at its `at`/`rotated`/`relative` (`add_to`), with its McStas parameters (`mcstas_values`: its
fields, and what it computes), a McStas string quoted here. A parameter McStas does not know
raises, so no field is dropped silently.

Coordinate system: McStas, z along the beam, y up, x to the left of the beam.
"""

from pathlib import Path

from mcstasscript.interface import instr

# McStas-generated files (.instr, .c, compiled binary) and simulation output go here, not in
# the project root. Created on use.
OUTPUT_DIR = Path(__file__).resolve().parents[3] / "mcstas_output"


def build(instrument, input_path=OUTPUT_DIR):
    """Return a McStasScript instrument of `instrument`: its instrument parameters and its
    components."""
    Path(input_path).mkdir(parents=True, exist_ok=True)
    inst = instr.McStas_instr(instrument.name, input_path=str(input_path))
    # a run sets its own values with `set_parameters`
    for param in instrument.instr_params:
        inst.add_parameter(param.name, value=param.value, unit=param.unit, comment=param.comment)
    for c in instrument.components.values():
        comp = c.add_to(inst)
        values = c.mcstas_values(instrument)
        if unknown := [p for p in values if p not in comp.parameter_names]:
            raise ValueError(f"{c.name} ({c.component_name}): no McStas parameter {unknown}")
        for parameter, value in values.items():
            if comp.parameter_types[parameter] == "string":
                value = f'"{value}"'  # a McStas string is a quoted C string
            setattr(comp, parameter, value)
    return inst


if __name__ == "__main__":
    from align_crystal.instrument import SingleCrystalDiffractometer, la2ni7

    # the sample, in the innermost goniometer arm
    sample = la2ni7(at=[0, 0, 0], relative="gonio_phi")
    diffractometer = SingleCrystalDiffractometer(sample)
    inst = build(diffractometer)
    inst.show_parameters()
    inst.show_components()
    inst.show_diagram()
    inst.write_full_instrument()  # show_instrument_file reads the file on disk: write it first
    inst.show_instrument_file(line_numbers=True)
