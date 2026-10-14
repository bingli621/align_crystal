from align_crystal.core import SingleCrystalDiffractometer, build_diffractometer
from align_crystal.yaml_io import yaml_loader, write_yaml


def test_write_then_read_gives_the_same_dict(tmp_path):
    data = {"name": "x", "a": {"b": [1, 2.5, None]}}
    write_yaml(data, tmp_path / "x.yaml")
    assert yaml_loader(tmp_path / "x.yaml") == data


def test_the_default_file_makes_the_diffractometer_that_the_code_makes():
    assert SingleCrystalDiffractometer.from_file() == build_diffractometer()


def test_the_diffractometer_roundtrips_through_a_yaml_file(diffractometer, tmp_path):
    inst = diffractometer({"detector": {"n_theta": 600}})
    write_yaml(inst.to_dict(), tmp_path / "out.yaml")
    assert SingleCrystalDiffractometer.from_file(tmp_path / "out.yaml") == inst
    written = yaml_loader(tmp_path / "out.yaml")
    assert written["source"]["energy_meV"] == "energy_meV"  # the control parameter
    assert written["controls"]["omega"] == {"value": 0.0, "unit": "deg", "comment": "goniometer rotation about +Y"}


def test_numbers_in_the_yaml_are_numbers():
    """PyYAML reads 1.0e10 (no sign in the exponent) as a string: flux must be a number."""
    assert isinstance(SingleCrystalDiffractometer.from_file().source.flux, float)
