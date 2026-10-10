import pytest

from align_crystal.file_io import load_config, save_config
from align_crystal.instrument import Diffractometer


def test_load_defaults():
    cfg = load_config()
    assert isinstance(cfg, Diffractometer)
    assert cfg.name == "align_crystal_diffractometer"


def test_load_overrides_only_given_keys(write_yaml):
    cfg = load_config(write_yaml("detector:\n  n_theta: 600\n  two_theta_range: [-100, -10]\n"))
    assert cfg.detector.n_theta == 600
    assert cfg.detector.two_theta_range == [-100, -10]
    assert cfg.detector.n_y == load_config().detector.n_y


def test_load_from_dict_and_from_instrument():
    cfg = load_config({"detector": {"n_theta": 100}})
    assert cfg.detector.n_theta == 100
    assert load_config(cfg) is cfg


@pytest.mark.parametrize("text", ["detector:\n  n_thetta: 600\n", "slitt:\n  size: 1\n"])
def test_unknown_key_raises(write_yaml, text):
    with pytest.raises(ValueError, match="Unknown"):
        load_config(write_yaml(text))


def test_unknown_placement_raises(write_yaml):
    with pytest.raises(ValueError, match="slit9"):
        load_config(write_yaml("placements:\n  slit9:\n    at: [0, 0, 1]\n"))


def test_name_override_only_on_components(write_yaml):
    assert load_config({"source": {"name": "my_source"}}).source.name == "my_source"
    with pytest.raises(ValueError, match="name"):
        load_config({"placements": {"name": "x"}})


def test_placement_override_keeps_the_rest(write_yaml):
    cfg = load_config(write_yaml("placements:\n  sample_pos:\n    at: [0, 0, 2.5]\n"))
    assert cfg.sample_pos.at == [0, 0, 2.5]
    assert cfg.sample_pos.relative == "source"  # untouched default


def test_save_roundtrip(tmp_path):
    cfg = load_config({"source": {"name": "my_source"}, "gonio_chi": {"angle": -5.9}})
    save_config(cfg, tmp_path / "out.yaml")
    assert load_config(tmp_path / "out.yaml") == cfg
