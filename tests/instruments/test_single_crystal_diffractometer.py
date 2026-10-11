import pytest

from instruments import SingleCrystalDiffractometer as Diffractometer


def test_the_default_file_names_the_components_in_beam_order(diffractometer):
    cfg = diffractometer()
    assert type(cfg) is Diffractometer
    assert list(cfg.components) == [
        "origin", "source", "slit1", "incident_monitor", "sample_pos",
        "gonio_omega", "gonio_chi", "gonio_phi", "crystal", "detector",
    ]  # fmt: skip


def test_the_source_derives_its_wavelength_and_the_diffractometer_its_focus_distance(diffractometer):
    source = diffractometer().source
    assert source.wavelength == pytest.approx(2.417262, abs=1e-5)  # 14 meV
    assert source.dist == 2.0  # the z of sample_pos
    moved = diffractometer({"placements": {"sample_pos": {"at": [0, 0, 2.5]}}})
    assert moved.source.dist == 2.5
    assert diffractometer({"source": {"dist": 1.5}}).source.dist == 1.5  # explicit wins


def test_the_source_focusing_on_nothing_raises(diffractometer):
    with pytest.raises(ValueError, match="The source focuses on 'nowhere'"):
        diffractometer({"source": {"focus_on": "nowhere"}})
