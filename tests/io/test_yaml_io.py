from align_crystal.instrument import (
    CtrlParam,
    SingleCrystalDiffractometer,
    aluminum,
    la2ni7,
)
from align_crystal.io import PARAMS_FILE, load, to_dict, write_yaml, yaml_loader


def test_write_then_read_gives_the_same_dict(tmp_path):
    data = {"name": "x", "a": {"b": [1, 2.5, None]}}
    write_yaml(data, tmp_path / "x.yaml")
    assert yaml_loader(tmp_path / "x.yaml") == data


def test_the_diffractometer_has_no_sample_by_default():
    crystal = la2ni7(at=[0, 0, 0], relative="gonio_phi")
    assert SingleCrystalDiffractometer().crystal is None
    assert "crystal" not in SingleCrystalDiffractometer().components
    assert (
        SingleCrystalDiffractometer([CtrlParam("crystal", crystal)]).crystal is crystal
    )  # as it is


def test_params_yaml_is_the_default_diffractometer_saved():
    """The reference file is the built one with an aluminium sample: laid over the one with no
    sample it gives the one the code makes with it, and over that one it changes nothing."""
    al = aluminum(at=[0, 0, 0], relative="gonio_phi")
    assert load(PARAMS_FILE) == SingleCrystalDiffractometer([CtrlParam("crystal", al)])
    assert load(PARAMS_FILE, [CtrlParam("crystal", al)]) == SingleCrystalDiffractometer(
        [CtrlParam("crystal", al)]
    )


def test_a_file_is_laid_over_the_code(tmp_path):
    write_yaml(
        {"slit": {"xwidth": 0.02, "yheight": None}, "detector": {"n_theta": 600}},
        tmp_path / "over.yaml",
    )
    d = load(tmp_path / "over.yaml")
    assert (d.slit.xwidth, d.slit.yheight) == (0.02, 0.01)  # given wins; null: as built
    assert (d.detector.n_theta, d.detector.n_y) == (600, 50)  # missing: as built
    assert d.source_dist == 2.0


def test_the_diffractometer_roundtrips_through_a_yaml_file(diffractometer, tmp_path):
    inst = diffractometer({"detector": {"n_theta": 600}})
    write_yaml(to_dict(inst), tmp_path / "out.yaml")
    assert load(tmp_path / "out.yaml") == inst
    written = yaml_loader(tmp_path / "out.yaml")
    assert written["source"]["ei"] == 14  # the operational parameter
    assert written["instr_params"]["omega"] == {
        "value": None,
        "unit": "deg",
        "comment": "goniometer rotation about +Y",
    }


def test_numbers_in_the_yaml_are_numbers():
    """PyYAML reads 1.0e10 (no sign in the exponent) as a string: flux must be a number."""
    assert isinstance(load(PARAMS_FILE).source.flux, float)


def test_a_diffractometer_with_another_crystal_roundtrips_through_a_yaml_file(tmp_path):
    inst = SingleCrystalDiffractometer(
        [CtrlParam("crystal", la2ni7(mosaic=60, at=[0, 0, 0], relative="gonio_phi"))]
    )
    write_yaml(to_dict(inst), tmp_path / "la2ni7.yaml")  # the crystal holds plain floats
    assert load(tmp_path / "la2ni7.yaml") == inst
