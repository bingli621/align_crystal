from pathlib import Path

import pytest

from align_crystal.instrument import CtrlParam, SingleCrystalDiffractometer, la2ni7
from align_crystal.mcstas.builder import build_instrument


def test_components_are_added_in_order_with_their_mcstas_names(tmp_path, diffractometer):
    inst = build_instrument(diffractometer(), input_path=tmp_path)
    assert [c.name for c in inst.component_list] == list(diffractometer().components)
    assert [c.component_name for c in inst.component_list] == [
        "Progress_bar", "Source_simple", "Slit", "Monitor", "Arm",
        "Arm", "Arm", "Arm", "Single_crystal", "Monitor_nD",
    ]  # fmt: skip


def test_the_parameters_and_the_goniometer_rotations(tmp_path, diffractometer):
    inst = build_instrument(diffractometer(), input_path=tmp_path)
    params = {p.name: p.value for p in inst.parameters}
    assert list(params) == ["wavelength", "omega", "chi", "phi"]  # the instrument parameters
    assert params["omega"] is None  # given by each run
    assert params["wavelength"] == pytest.approx(2.417262, abs=1e-5)  # calculated from ei = 14 meV
    source = next(c for c in inst.component_list if c.name == "source")
    assert source.lambda0 == "wavelength"  # the instrument parameter
    assert source.dlambda == 0 and source.E0 is None  # E0 unset: McStas uses lambda0
    chi = next(c for c in inst.component_list if c.name == "gonio_chi")
    assert chi.ROTATED_data == [0, 0, "-chi"] and chi.ROTATED_reference == "gonio_omega"


def test_without_ei_the_wavelength_is_set_by_each_run(tmp_path):
    inst = build_instrument(SingleCrystalDiffractometer(), input_path=tmp_path)
    assert {p.name: p.value for p in inst.parameters}["wavelength"] is None


def test_the_crystal_of_the_diffractometer_sets_the_mcstas_crystal(tmp_path):
    crystal = la2ni7(mosaic=60, at=[0, 0, 0], relative="gonio_phi")
    cfg = SingleCrystalDiffractometer([CtrlParam("crystal", crystal), CtrlParam("ei", 14, "meV")])
    inst = build_instrument(cfg, input_path=tmp_path)
    crystal = next(c for c in inst.component_list if c.name == "crystal")
    assert crystal.mosaic == 60 and cfg.crystal.reflections in crystal.reflections
    assert Path(
        crystal.reflections.strip('"')
    ).is_absolute()  # McStas gets the full path of the CIF
    assert crystal.xwidth == cfg.crystal.xwidth
