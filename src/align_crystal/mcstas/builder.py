"""Build the McStas instrument (McStasScript) of any `Instrument`.

Its instrument parameters, then its components one by one, in the order of the beam (McStas
positions are relative to earlier ones). Each is added as its `component_name`, named its
`name`, at its `at`/`rotated`/`relative` (`add_to`), with its McStas parameters
(`mcstas_parameters`: its fields, and what it computes), a McStas string quoted here. A field
McStas does not know is left out (what it computes from); a computed parameter McStas does not
know raises.

Coordinate system: McStas, z along the beam, y up, x to the left of the beam.
"""

from dataclasses import fields
from pathlib import Path

from mcstasscript.interface import instr

# McStas-generated files (.instr, .c, compiled binary) and simulation output go here, not in
# the project root. Created on use.
OUTPUT_DIR = Path(__file__).resolve().parents[3] / "mcstas_output"


def build(instrument, input_path=OUTPUT_DIR):
    """Return a McStasScript instrument of `instrument`: its instrument parameters and its
    components."""
    Path(input_path).mkdir(parents=True, exist_ok=True)
    mcstas_instr = instr.McStas_instr(instrument.name, input_path=str(input_path))
    # a run sets its own values with `set_parameters`
    for param in instrument.instr_params:
        mcstas_instr.add_parameter(
            param.name, value=param.value, unit=param.unit, comment=param.comment
        )
    for component in instrument.components.values():
        mcstas_comp = component.add_to(mcstas_instr)
        known = set(mcstas_comp.parameter_names)  # by its McStas component
        field_names = {f.name for f in fields(component)}
        parameters = component.mcstas_parameters(instrument)
        if unknown := sorted(parameters.keys() - known - field_names):  # computed, not McStas's
            raise ValueError(
                f"{component.name} ({component.component_name}): no McStas parameter {unknown}"
            )
        for name, value in parameters.items():
            if name not in known:
                continue  # a field it computes from
            if mcstas_comp.parameter_types[name] == "string":
                value = f'"{value}"'  # a McStas string is a quoted C string
            setattr(mcstas_comp, name, value)
    return mcstas_instr


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
