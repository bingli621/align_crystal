import subprocess
import sys
from dataclasses import FrozenInstanceError

import pytest

from align_crystal.instrument import Params, Source_simple, aluminum
from align_crystal.instrument import SingleCrystalDiffractometer as Diffractometer
from align_crystal.io import from_dict, to_dict


def test_the_default_file_names_the_components_in_beam_order(diffractometer):
    cfg = diffractometer()
    assert type(cfg) is Diffractometer
    assert list(cfg.components) == [
        "origin", "source", "slit", "incident_monitor", "sample_pos",
        "gonio_omega", "gonio_chi", "gonio_phi", "sample", "detector",
    ]  # fmt: skip
    assert cfg.slit is cfg.components["slit"]


def test_from_dict_then_to_dict_roundtrip(diffractometer):
    cfg = diffractometer()
    data = to_dict(cfg)
    assert list(data)[:4] == ["instrument", "name", "params", "origin"]
    assert list(data["slit"]) == [
        "component",
        "xwidth",
        "yheight",
        "at",
        "rotated",
        "relative",
        "position",
    ]
    assert from_dict(data) == cfg


def test_the_instrument_parameters_of_the_diffractometer(diffractometer):
    values = {p.name: p.value for p in diffractometer().instr_params}
    assert list(values) == ["wavelength", "omega", "chi", "phi"]
    assert values["wavelength"] == pytest.approx(2.417262, abs=1e-5)  # from ei
    assert values["omega"] == 0 and values["chi"] == 0  # the defaults


def test_the_wavelength_is_the_one_of_ei(diffractometer):
    assert diffractometer().params.ei == 14  # given when the instrument was made
    assert diffractometer().instr_params[0].value == pytest.approx(2.417262, abs=1e-5)
    from_file = diffractometer({"params": {"ei": 25}})  # a file's ei: the wavelength follows
    assert from_file.instr_params[0].value == pytest.approx(1.808914, abs=1e-5)
    started = diffractometer({"params": {"omega": 30}})
    assert {p.name: p.value for p in started.instr_params}["omega"] == 30


def test_core_imports_no_yaml_and_no_adapter():
    """The entities import no adapter: no YAML, no io, no McStas."""
    code = (
        "import sys, align_crystal.instrument;"
        "bad = [m for m in sys.modules if m == 'yaml' or m.startswith(('align_crystal.io', 'align_crystal.mcstas'))];"
        "assert not bad, bad"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_the_params_are_given_when_it_is_made():
    assert Diffractometer().params == Params(ei=14, omega=0, chi=0, phi=0)  # the defaults
    d = Diffractometer(params=Params(ei=25, omega=30))
    assert d.params.ei == 25
    values = {p.name: p.value for p in d.instr_params}
    assert (values["omega"], values["chi"], values["phi"]) == (30, 0, 0)


def test_the_params_change_only_with_update_params():
    d = Diffractometer()
    with pytest.raises(FrozenInstanceError):
        d.params.ei = 25  # frozen
    with pytest.raises(AttributeError):
        d.params = {"ei": 25}
    d.update_params(ei=25, omega=10)
    run = {p.name: p.value for p in d.instr_params}
    assert run["wavelength"] == pytest.approx(1.808914, abs=1e-5) and run["omega"] == 10
    with pytest.raises(TypeError, match="omgea"):
        d.update_params(omgea=1)


def test_the_source_gives_the_wavelength_of_an_energy():
    assert Source_simple.wavelength_from_ei(14) == pytest.approx(2.417262, abs=1e-5)


def test_the_positions_follow_the_relative_frames_and_the_angles():
    sample = aluminum(at=[0, 0, 0.1], relative="gonio_phi")  # 10 cm along the beam, at zero angles
    d = Diffractometer(sample)
    assert d.positions()["slit"] == pytest.approx([0, 0, 1.0])
    assert d.positions()["sample"] == pytest.approx([0, 0, 2.1])
    d.update_params(omega=90)
    assert d.positions()["sample"] == pytest.approx([0.1, 0, 2.0])  # +z turned to +x
    d.update_params(chi=90)
    assert d.positions()["sample"] == pytest.approx([0.1, 0, 2.0])  # along the chi axis
