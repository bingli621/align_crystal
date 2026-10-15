import subprocess
import sys

import pytest

from align_crystal.instrument import CtrlParam, complete_values
from align_crystal.instrument import SingleCrystalDiffractometer as Diffractometer
from align_crystal.io import from_dict, to_dict


def test_the_default_file_names_the_components_in_beam_order(diffractometer):
    cfg = diffractometer()
    assert type(cfg) is Diffractometer
    assert list(cfg.components) == [
        "origin", "source", "slit", "incident_monitor", "sample_pos",
        "gonio_omega", "gonio_chi", "gonio_phi", "crystal", "detector",
    ]  # fmt: skip
    assert cfg.slit is cfg.components["slit"]


def test_from_dict_then_to_dict_roundtrip(diffractometer):
    cfg = diffractometer()
    data = to_dict(cfg)
    assert list(data)[:3] == ["name", "instr_params", "origin"]
    assert list(data["slit"]) == ["component", "xwidth", "yheight", "at", "rotated", "relative"]
    assert from_dict(data) == cfg


def test_the_focus_distance_is_computed_when_used(diffractometer):
    d = diffractometer()
    assert d.source.dist is None and d.source_dist == 2.0  # the z of sample_pos
    d.sample_pos.at = [0, 0, 2.5]  # a change is followed
    assert d.source_dist == 2.5
    assert "dist" not in to_dict(d)["source"]  # not saved: a derived value
    assert diffractometer({"source": {"dist": 1.5}}).source_dist == 1.5  # explicit wins


def test_a_component_can_be_changed_and_validated_again(diffractometer):
    d = diffractometer()
    d.slit.xwidth = 0.02
    assert to_dict(d.validate())["slit"]["xwidth"] == 0.02
    d.slit.xwidth = "widht"
    with pytest.raises(ValueError, match="slit.xwidth uses 'widht'"):
        d.validate()


def test_the_source_focusing_on_nothing_raises(diffractometer):
    with pytest.raises(ValueError, match="The source focuses on 'nowhere'"):
        diffractometer({"source": {"focus_on": "nowhere"}})


def test_a_null_that_cannot_be_derived_raises(diffractometer):
    with pytest.raises(ValueError, match="slit.xwidth"):
        diffractometer({"slit": {"xwidth": None}})


def test_the_instrument_parameters_of_the_diffractometer(diffractometer):
    cfg = diffractometer()
    run = {p.name: p.value for p in cfg.instrument_param(omega=12)}
    assert list(run) == ["wavelength", "omega", "chi", "phi"]
    assert run["wavelength"] == pytest.approx(2.417262, abs=1e-5)  # from ei
    assert run["omega"] == 12 and run["chi"] is None  # given by each run
    assert cfg.instr_params[1].value is None  # a run does not change the instrument
    with pytest.raises(ValueError, match="not set: chi, phi"):
        complete_values(cfg.instrument_param(omega=12))
    assert complete_values(cfg.instrument_param(omega=12, chi=0, phi=0))["phi"] == 0
    assert (
        complete_values(cfg.instrument_param(wavelength=3.0, omega=0, chi=0, phi=0))["wavelength"]
        == 3.0
    )  # a run may set it
    with pytest.raises(ValueError, match="not set: wavelength"):
        complete_values(Diffractometer().instrument_param(omega=0, chi=0, phi=0))
    with pytest.raises(ValueError, match="Unknown instrument parameter"):
        cfg.instrument_param(psi=1)


def test_the_source_converts_the_operational_energy_to_a_wavelength(diffractometer):
    assert diffractometer().source.ei == 14  # given when the instrument was made
    assert diffractometer().source.wavelength == pytest.approx(2.417262, abs=1e-5)
    assert diffractometer({"source": {"ei": 25}}).source.ei == 25
    with pytest.raises(ValueError, match="ei"):
        _ = Diffractometer().source.wavelength
    started = diffractometer({"instr_params": {"omega": {"value": 30}}})
    assert {p.name: p.value for p in started.instrument_param()}["omega"] == 30


def test_a_component_naming_an_unknown_control_raises(diffractometer):
    with pytest.raises(ValueError, match="slit.xwidth uses 'widht'"):
        diffractometer({"slit": {"xwidth": "widht"}})
    with pytest.raises(ValueError, match="gonio_chi.rotated uses 'chii'"):
        diffractometer({"gonio_chi": {"rotated": [0, 0, "-chii"]}})


def test_a_control_needs_a_value_and_no_unknown_keys(diffractometer):
    data = to_dict(diffractometer())
    del data["instr_params"]["omega"]["value"]
    with pytest.raises(ValueError, match="instr_params.omega needs a value"):
        from_dict(data)
    with pytest.raises(ValueError, match="instr_params.omega.units"):
        diffractometer({"instr_params": {"omega": {"units": "deg"}}})


def test_a_control_named_like_a_role_raises(diffractometer):
    with pytest.raises(ValueError, match="'slit' is also a component name"):
        diffractometer({"instr_params": {"slit": {"value": 1}}})


def test_core_imports_no_yaml_and_no_adapter():
    """The entities import no adapter: no YAML, no io, no McStas."""
    code = (
        "import sys, align_crystal.instrument;"
        "bad = [m for m in sys.modules if m == 'yaml' or m.startswith(('align_crystal.io', 'align_crystal.mcstas'))];"
        "assert not bad, bad"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_the_components_are_fixed_a_missing_or_unknown_one_raises(diffractometer):
    data = to_dict(diffractometer())
    extra = {**data, "slit2": data["slit"]}
    with pytest.raises(ValueError, match="slit2"):
        from_dict(extra)
    missing = {k: v for k, v in data.items() if k != "detector"}
    with pytest.raises(ValueError, match="detector"):
        from_dict(missing)


def test_a_component_of_the_wrong_class_raises(diffractometer):
    data = to_dict(diffractometer())
    data["slit"] = {"component": "Arm", "at": [0, 0, 1.0], "rotated": None, "relative": "source"}
    with pytest.raises(ValueError, match="slit must be a Slit, not Arm"):
        from_dict(data)


def test_the_parameters_the_components_use(diffractometer):
    d = diffractometer()
    assert d.params_used() == {"wavelength", "omega", "chi", "phi"}
    assert d.params_used(until="sample_pos") == {"wavelength"}  # before the goniometer


def test_the_control_parameters_are_a_list_of_known_names():
    crystal_param = CtrlParam("crystal", None)
    assert Diffractometer([crystal_param, CtrlParam("ei", 14, "meV")]).source.ei == 14
    with pytest.raises(ValueError, match="Unknown control parameter 'energy'"):
        Diffractometer([CtrlParam("energy", 14)])
    with pytest.raises(ValueError, match="'ei' is given twice"):
        Diffractometer([CtrlParam("ei", 14), CtrlParam("ei", 25)])
