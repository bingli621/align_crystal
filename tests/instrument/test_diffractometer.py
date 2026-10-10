import copy

import pytest

from align_crystal.file_io import load_config
from align_crystal.file_io.loader import _read_yaml
from align_crystal.instrument import Diffractometer, Instrument, Source_simple


def test_components_are_in_beam_order():
    assert list(load_config().components) == [
        "origin",
        "source",
        "slit1",
        "incident_monitor",
        "sample_pos",
        "gonio_omega",
        "gonio_chi",
        "gonio_phi",
        "crystal",
        "detector",
    ]


def test_is_an_instrument():
    assert isinstance(load_config(), Instrument)


def test_attribute_access_and_unknown_role():
    cfg = load_config()
    assert cfg.source is cfg.components["source"]
    assert isinstance(cfg.source, Source_simple)
    with pytest.raises(AttributeError):
        cfg.nonexistent


def test_wavelength_derived_from_energy():
    assert load_config().source.wavelength == pytest.approx(2.417262, abs=1e-5)  # 14 meV
    assert load_config({"source": {"energy_meV": 81.80421}}).source.wavelength == pytest.approx(1.0)


def test_explicit_wavelength_wins():
    assert load_config({"source": {"wavelength": 1.8}}).source.wavelength == 1.8


def test_source_focus_follows_the_sample_position():
    assert load_config().source.dist == 2.0
    cfg = load_config({"placements": {"sample_pos": {"at": [0, 0, 2.5]}}})
    assert cfg.source.dist == 2.5
    assert load_config({"source": {"dist": 1.5}}).source.dist == 1.5  # explicit wins


def test_direct_construction_is_resolved():
    """The focus distance is derived by the Diffractometer itself, not only by load_config."""
    raw = _read_yaml(Diffractometer.PARAMS_FILE)
    assert raw["source"]["dist"] is None
    inst = Diffractometer.from_dict(raw)
    assert inst.source.dist == inst.sample_pos.at[2] == 2.0


def test_unresolvable_null_raises():
    with pytest.raises(ValueError, match="source.radius"):
        load_config({"source": {"radius": None}})


def test_placements_are_recorded_on_the_components():
    chi = load_config().gonio_chi
    assert chi.at == [0, 0, 0]
    assert chi.rotated == [0, 0, "-chi"]
    assert chi.relative == "gonio_omega"


def test_survives_copy():
    cfg = load_config()
    assert copy.deepcopy(cfg) == cfg
