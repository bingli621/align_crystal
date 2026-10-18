import subprocess
import sys

import pytest

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
    assert list(data)[:3] == ["name", "params", "origin"]
    assert list(data["slit"]) == ["component", "xwidth", "yheight", "at", "rotated", "relative"]
    assert from_dict(data) == cfg


def test_the_focus_distance_is_computed_when_used(diffractometer):
    d = diffractometer()
    assert d.source.dist is None and d.source_dist == 2.0  # the z of sample_pos
    d.sample_pos.at = [0, 0, 2.5]  # a change is followed
    assert d.source_dist == 2.5
    assert "dist" not in to_dict(d)["source"]  # not saved: a derived value
    assert diffractometer({"source": {"dist": 1.5}}).source_dist == 1.5  # explicit wins


def test_the_instrument_parameters_of_the_diffractometer(diffractometer):
    cfg = diffractometer()
    run = {p.name: p.value for p in cfg.instrument_param(omega=12)}
    assert list(run) == ["wavelength", "omega", "chi", "phi"]
    assert run["wavelength"] == pytest.approx(2.417262, abs=1e-5)  # from ei
    assert run["omega"] == 12 and run["chi"] == 0  # the run's, and the default
    assert cfg.instr_params[1].value == 0  # a run does not change the instrument
    assert cfg.instrument_param(wavelength=3.0)[0].value == 3.0  # a run may set it


def test_the_wavelength_is_the_one_of_ei(diffractometer):
    assert diffractometer().params["ei"] == 14  # given when the instrument was made
    assert diffractometer().wavelength == pytest.approx(2.417262, abs=1e-5)
    from_file = diffractometer({"params": {"ei": 25}})  # a file's ei: the wavelength follows
    assert from_file.instr_params[0].value == pytest.approx(1.808914, abs=1e-5)
    started = diffractometer({"params": {"omega": 30}})
    assert {p.name: p.value for p in started.instrument_param()}["omega"] == 30


def test_core_imports_no_yaml_and_no_adapter():
    """The entities import no adapter: no YAML, no io, no McStas."""
    code = (
        "import sys, align_crystal.instrument;"
        "bad = [m for m in sys.modules if m == 'yaml' or m.startswith(('align_crystal.io', 'align_crystal.mcstas'))];"
        "assert not bad, bad"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_the_params_are_given_when_it_is_made():
    assert dict(Diffractometer().params) == {"ei": 14, "omega": 0, "chi": 0, "phi": 0}  # defaults
    d = Diffractometer(ei=25, omega=30)
    assert d.params["ei"] == 25
    run = {p.name: p.value for p in d.instrument_param(chi=1)}
    assert (run["omega"], run["chi"], run["phi"]) == (30, 1, 0)
    assert {p.name: p.value for p in d.instrument_param(omega=5)}["omega"] == 5  # a run wins


def test_the_params_change_only_with_update_params():
    d = Diffractometer()
    d.params["ei"] = 25  # a copy: the diffractometer does not change
    assert d.params["ei"] == 14
    with pytest.raises(AttributeError):
        d.params = {"ei": 25}
    d.update_params(ei=25, omega=10)
    run = {p.name: p.value for p in d.instr_params}
    assert run["wavelength"] == pytest.approx(1.808914, abs=1e-5) and run["omega"] == 10
    with pytest.raises(ValueError, match="omgea"):
        d.update_params(omgea=1)
