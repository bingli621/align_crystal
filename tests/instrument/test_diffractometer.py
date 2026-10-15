import subprocess
import sys

import pytest

from align_crystal.instrument import SingleCrystalDiffractometer as Diffractometer


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
    data = cfg.to_dict()
    assert list(data)[:3] == ["name", "controls", "origin"]
    assert list(data["slit"]) == ["component", "xwidth", "yheight", "at", "rotated", "relative"]
    assert Diffractometer.from_dict(data) == cfg


def test_the_focus_distance_is_computed_when_used(diffractometer):
    d = diffractometer()
    assert d.source.dist is None and d.source_dist == 2.0  # the z of sample_pos
    d.sample_pos.at = [0, 0, 2.5]  # a change is followed
    assert d.source_dist == 2.5
    assert "dist" not in d.to_dict()["source"]  # not saved: a derived value
    assert diffractometer({"source": {"dist": 1.5}}).source_dist == 1.5  # explicit wins


def test_a_component_can_be_changed_and_validated_again(diffractometer):
    d = diffractometer()
    d.slit.xwidth = 0.02
    assert d.validate().to_dict()["slit"]["xwidth"] == 0.02
    d.slit.xwidth = "widht"
    with pytest.raises(ValueError, match="slit.xwidth uses 'widht'"):
        d.validate()


def test_the_source_focusing_on_nothing_raises(diffractometer):
    with pytest.raises(ValueError, match="The source focuses on 'nowhere'"):
        diffractometer({"source": {"focus_on": "nowhere"}})


def test_a_null_that_cannot_be_derived_raises(diffractometer):
    with pytest.raises(ValueError, match="slit.xwidth"):
        diffractometer({"slit": {"xwidth": None}})


def test_the_control_parameters_of_the_diffractometer(diffractometer):
    cfg = diffractometer()
    controls = cfg.control_param(omega=12)
    assert list(controls) == ["energy_meV", "omega", "chi", "phi"]
    assert controls["energy_meV"] is None  # no calculated value: every run sets it
    assert controls["omega"] == 12 and controls["chi"] == 0.0
    assert cfg.controls["omega"] == 0.0  # a run does not change the instrument
    with pytest.raises(ValueError, match="not set: energy_meV"):
        controls.complete()
    assert controls.replace(energy_meV=14).complete()["energy_meV"] == 14
    with pytest.raises(ValueError, match="Unknown control parameter"):
        cfg.control_param(psi=1)


def test_the_file_declares_the_controls_and_the_source_names_its_energy(diffractometer):
    assert diffractometer().source.E0 == "energy_meV"
    fixed = diffractometer({"source": {"E0": 14}})  # a fixed energy is also allowed
    assert fixed.source.E0 == 14
    started = diffractometer({"controls": {"omega": {"value": 30}}})
    assert started.control_param()["omega"] == 30


def test_a_component_naming_an_unknown_control_raises(diffractometer):
    with pytest.raises(ValueError, match="slit.xwidth uses 'widht'"):
        diffractometer({"slit": {"xwidth": "widht"}})
    with pytest.raises(ValueError, match="gonio_chi.rotated uses 'chii'"):
        diffractometer({"gonio_chi": {"rotated": [0, 0, "-chii"]}})


def test_a_control_needs_a_value_and_no_unknown_keys(diffractometer):
    data = diffractometer().to_dict()
    del data["controls"]["omega"]["value"]
    with pytest.raises(ValueError, match="controls.omega needs a value"):
        Diffractometer.from_dict(data)
    with pytest.raises(ValueError, match="controls.omega.units"):
        diffractometer({"controls": {"omega": {"units": "deg"}}})


def test_a_control_named_like_a_role_raises(diffractometer):
    with pytest.raises(ValueError, match="'slit' is also a component name"):
        diffractometer({"controls": {"slit": {"value": 1}}})


def test_core_imports_no_yaml_and_no_adapter():
    """The entities know no file format and no adapter (YAML is only loaded by `build_diffractometer(file=...)`)."""
    code = (
        "import sys, align_crystal.instrument;"
        "bad = [m for m in sys.modules if m == 'yaml' or m.startswith(('align_crystal.yaml_io', 'align_crystal.mcstas'))];"
        "assert not bad, bad"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_the_components_are_fixed_a_missing_or_unknown_one_raises(diffractometer):
    data = diffractometer().to_dict()
    extra = {**data, "slit2": data["slit"]}
    with pytest.raises(ValueError, match="slit2"):
        Diffractometer.from_dict(extra)
    missing = {k: v for k, v in data.items() if k != "detector"}
    with pytest.raises(ValueError, match="detector"):
        Diffractometer.from_dict(missing)
