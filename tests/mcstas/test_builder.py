import pytest

from align_crystal.mcstas.builder import build_instrument
from align_crystal.samples import la2ni7


def test_components_are_added_in_order_with_their_mcstas_names(tmp_path, diffractometer):
    inst = build_instrument(diffractometer(), input_path=tmp_path)
    assert [c.name for c in inst.component_list] == list(diffractometer().components)
    assert [c.component_name for c in inst.component_list] == [
        "Progress_bar", "Source_simple", "Slit", "Monitor", "Arm",
        "Arm", "Arm", "Arm", "Single_crystal", "Monitor_nD",
    ]  # fmt: skip


def test_the_parameters_and_the_goniometer_rotations(tmp_path, diffractometer):
    inst = build_instrument(diffractometer({"gonio_omega": {"angle": 30}}), input_path=tmp_path)
    params = {p.name: p.value for p in inst.parameters}
    assert params["omega"] == 30 and params["wavelength"] == pytest.approx(2.417262, abs=1e-5)
    chi = next(c for c in inst.component_list if c.name == "gonio_chi")
    assert chi.ROTATED_data == [0, 0, "-chi"] and chi.ROTATED_reference == "gonio_omega"


def test_the_sample_sets_the_crystal(tmp_path, diffractometer):
    sample = la2ni7(mosaic=60)
    inst = build_instrument(diffractometer(), sample=sample, input_path=tmp_path)
    crystal = next(c for c in inst.component_list if c.name == "crystal")
    assert crystal.mosaic == 60 and sample.reflections in crystal.reflections
