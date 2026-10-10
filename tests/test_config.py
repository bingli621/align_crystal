import pytest

from align_crystal.instrument import DiffractometerConfig, Source, load_config, save_config
from align_crystal.mcstas.builder import build_instrument


def test_defaults_match_14_mev():
    assert load_config().source.wavelength == pytest.approx(2.417262, abs=1e-5)


def test_nulls_are_resolved_on_load():
    cfg = load_config()
    assert isinstance(cfg.source, Source)
    assert cfg.source.wavelength is not None and cfg.source.dist == 2.0


def test_load_overrides_only_given_keys(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("detector:\n  n_theta: 600\n  two_theta_range: [-100, -10]\n")
    cfg = load_config(p)
    assert cfg.detector.n_theta == 600
    assert cfg.detector.two_theta_range == [-100, -10]
    assert cfg.detector.n_y == load_config().detector.n_y


@pytest.mark.parametrize(
    "text", ["detector:\n  n_thetta: 600\n", "slitt:\n  size: 1\n"]
)
def test_unknown_key_raises(tmp_path, text):
    p = tmp_path / "c.yaml"
    p.write_text(text)
    with pytest.raises(ValueError, match="Unknown"):
        load_config(p)


def test_explicit_wavelength_wins():
    assert load_config({"source": {"wavelength": 1.8}}).source.wavelength == 1.8


def test_unresolvable_null_raises():
    with pytest.raises(ValueError, match="radius"):
        load_config({"source": {"radius": None}})


def test_save_roundtrip(tmp_path):
    cfg = load_config()
    save_config(cfg, tmp_path / "out.yaml")
    assert load_config(tmp_path / "out.yaml") == cfg


def test_build_from_yaml_path(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("name: example_run\ngonio_omega:\n  angle: 30\n")
    assert build_instrument(load_config(p)).name == "example_run"


def test_build_from_config_object():
    cfg = load_config({"name": "obj"})
    assert isinstance(cfg, DiffractometerConfig)
    assert build_instrument(cfg).name == "obj"


def test_placement_override_and_sample_dist(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("placements:\n  sample_pos:\n    at: [0, 0, 2.5]\n")
    cfg = load_config(p)
    assert cfg.placements["sample_pos"].at == [0, 0, 2.5]
    assert cfg.placements["sample_pos"].relative == "source"  # untouched default
    assert cfg.source.dist == 2.5  # derived from sample_pos


def test_unknown_placement_raises(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("placements:\n  slit9:\n    at: [0, 0, 1]\n")
    with pytest.raises(ValueError, match="slit9"):
        load_config(p)


def test_build_from_dict_overrides():
    inst = build_instrument(
        load_config({"name": "from_dict", "detector": {"n_theta": 100}})
    )
    assert inst.name == "from_dict"


def test_goniometer_rotation_in_instrument():
    inst = build_instrument(load_config())
    chi = next(c for c in inst.component_list if c.name == "gonio_chi")
    assert chi.ROTATED_data == [0, 0, "-chi"]


def test_component_name_and_type_from_config():
    inst = build_instrument(load_config({"source": {"name": "my_source"}}))
    names = {c.name: c for c in inst.component_list}
    assert "my_source" in names and "source" not in names
    assert names["slit1"].AT_reference == "my_source"  # references follow the new name
    assert names["slit1"].component_name == "Slit"
