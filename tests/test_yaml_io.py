from instruments import SingleCrystalDiffractometer
from align_crystal.yaml_io import yaml_loader, write_yaml


def test_write_then_read_gives_the_same_dict(tmp_path):
    data = {"name": "x", "a": {"b": [1, 2.5, None]}}
    write_yaml(data, tmp_path / "x.yaml")
    assert yaml_loader(tmp_path / "x.yaml") == data


def test_the_default_file_makes_the_diffractometer_that_the_code_makes():
    assert SingleCrystalDiffractometer.from_file() == SingleCrystalDiffractometer.from_parameters()


def test_the_diffractometer_roundtrips_through_a_yaml_file(diffractometer, tmp_path):
    inst = diffractometer({"gonio_chi": {"angle": -5.9}})
    write_yaml(inst.to_dict(), tmp_path / "out.yaml")
    assert SingleCrystalDiffractometer.from_file(tmp_path / "out.yaml") == inst


def test_numbers_in_the_yaml_are_numbers():
    """PyYAML reads 1.0e10 (no sign in the exponent) as a string: flux must be a number."""
    assert isinstance(SingleCrystalDiffractometer.from_file().source.flux, float)
