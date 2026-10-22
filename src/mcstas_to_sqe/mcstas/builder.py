"""Build the McStas instrument (McStasScript) of any `Instrument`.

Its instrument parameters, then its components one by one, in the order of the beam (McStas
positions are relative to earlier ones). Each is added as its `component_name`, named its
`name`, at its `at`/`rotated`/`relative` (`add_to`), with its McStas parameters
(`mcstas_parameters`: its fields, and what it computes), a McStas string quoted here. A field
McStas does not know is left out (what it computes from); a computed parameter McStas does not
know raises.

Coordinate system: McStas, z along the beam, y up, x to the left of the beam.
"""

from dataclasses import asdict, fields
from pathlib import Path

from mcstasscript.interface import instr

from mcstas_to_sqe import PROJECT_ROOT

# McStas-generated files (.instr, .c, compiled binary), McStasScript's input_path: mcrun runs
# here. Created by `build_mcstas`.
INPUT_DIR = PROJECT_ROOT / "mcstas_input"


def _set_parameters(mcstas_comp, component, instrument):
    """Set the McStas parameters of `component` (of `instrument`) on `mcstas_comp`, its
    McStasScript component. Each of `component.mcstas_parameters` is either:

    - a McStas parameter: set (a string quoted);
    - a field McStas does not take: left out, the component only computes from it (the
      detector's `theta_bins`, put into its `options`);
    - neither, so computed under a name McStas does not take: ValueError (a typo, likely).
    """
    mcstas_names = set(mcstas_comp.parameter_names)  # what the McStas component takes
    field_names = {f.name for f in fields(component)}
    all_params = component.mcstas_parameters(instrument)  # its fields, and what it computes

    # checked before any is set, so the error names every one
    if unknown := sorted(all_params.keys() - mcstas_names - field_names):
        raise ValueError(
            f"{component.name} ({component.component_name}): no McStas parameter {unknown}"
        )

    for name, value in all_params.items():
        if name not in mcstas_names:
            continue  # a field the component computes from: not for McStas
        if mcstas_comp.parameter_types[name] == "string":
            value = f'"{value}"'  # McStas takes a string as a quoted C string
        setattr(mcstas_comp, name, value)  # McStasScript: one attribute per McStas parameter


def build_mcstas(instrument, input_path: str | Path | None = None):
    """Return a McStasScript instrument of `instrument`: its instrument parameters and its
    components. Its files go into `input_path` (None for `INPUT_DIR`), created if not there yet."""

    input_path = Path(input_path or INPUT_DIR)
    input_path.mkdir(parents=True, exist_ok=True)

    mcstas_instr = instr.McStas_instr(instrument.name, input_path=str(input_path))
    # a run sets its own values with `set_parameters`
    for param in instrument.instr_params:
        mcstas_instr.add_parameter(**asdict(param))

    for component in instrument.components.values():
        mcstas_comp = component.add_to(mcstas_instr)  # placed: AT, ROTATED, RELATIVE
        _set_parameters(mcstas_comp, component, instrument)
    return mcstas_instr
