import subprocess
import sys

import pytest

from align_crystal.core import SingleCrystalDiffractometer as Diffractometer


def test_the_default_file_names_the_components_in_beam_order(diffractometer):
    cfg = diffractometer()
    assert type(cfg) is Diffractometer
    assert list(cfg.components) == [
        "origin", "source", "slit1", "incident_monitor", "sample_pos",
        "gonio_omega", "gonio_chi", "gonio_phi", "crystal", "detector",
    ]  # fmt: skip
    assert cfg.slit1 is cfg.components["slit1"] and cfg.slit1.name == "slit1"  # named by role


def test_a_name_in_the_section_wins_over_the_role(diffractometer):
    assert diffractometer({"slit1": {"name": "other"}}).slit1.name == "other"


def test_from_dict_then_to_dict_roundtrip(diffractometer):
    cfg = diffractometer()
    data = cfg.to_dict()
    assert list(data)[:3] == ["name", "controls", "origin"]
    assert list(data["slit1"]) == ["component", "name", "size", "at", "rotated", "relative"]
    assert Diffractometer.from_dict(data) == cfg


def test_from_file_reads_the_file_with_the_loader_it_is_given(diffractometer):
    seen = []

    def loader(file):
        seen.append(file)
        return diffractometer().to_dict()

    assert Diffractometer.from_file("any.thing", loader) == diffractometer()
    assert seen == ["any.thing"]


def test_the_diffractometer_derives_the_focus_distance(diffractometer):
    source = diffractometer().source
    assert source.dist == 2.0  # the z of sample_pos
    moved = diffractometer({"sample_pos": {"at": [0, 0, 2.5]}})
    assert moved.source.dist == 2.5
    assert diffractometer({"source": {"dist": 1.5}}).source.dist == 1.5  # explicit wins


def test_the_source_focusing_on_nothing_raises(diffractometer):
    with pytest.raises(ValueError, match="The source focuses on 'nowhere'"):
        diffractometer({"source": {"focus_on": "nowhere"}})


def test_a_null_that_cannot_be_derived_raises(diffractometer):
    with pytest.raises(ValueError, match="slit1.size"):
        diffractometer({"slit1": {"size": None}})


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
    assert diffractometer().source.energy_meV == "energy_meV"
    fixed = diffractometer({"source": {"energy_meV": 14}})  # a fixed energy is also allowed
    assert fixed.source.energy_meV == 14
    started = diffractometer({"controls": {"omega": {"value": 30}}})
    assert started.control_param()["omega"] == 30


def test_a_component_naming_an_unknown_control_raises(diffractometer):
    with pytest.raises(ValueError, match="slit1.size uses 'widht'"):
        diffractometer({"slit1": {"size": "widht"}})
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
    with pytest.raises(ValueError, match="'slit1' is also a role"):
        diffractometer({"controls": {"slit1": {"value": 1}}})


def test_core_imports_no_yaml_and_no_adapter():
    """The entities know no file format and no adapter (YAML is only loaded by `from_file`)."""
    code = (
        "import sys, align_crystal.core;"
        "bad = [m for m in sys.modules if m == 'yaml' or m.startswith(('align_crystal.yaml_io', 'align_crystal.mcstas'))];"
        "assert not bad, bad"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
