import pytest

from align_crystal.file_io import load_config
from align_crystal.mcstas.builder import build_instrument


@pytest.fixture
def build(tmp_path):
    """build(config) -> McStasScript instrument, generated files kept in the test's tmp folder."""
    return lambda config=None: build_instrument(load_config(config), input_path=tmp_path)


def _components(inst):
    return {c.name: c for c in inst.component_list}


def test_components_in_order(build):
    inst = build()
    assert [c.name for c in inst.component_list] == list(load_config().components)
    assert [c.component_name for c in inst.component_list] == [
        "Progress_bar",
        "Source_simple",
        "Slit",
        "Monitor",
        "Arm",
        "Arm",
        "Arm",
        "Arm",
        "Single_crystal",
        "Monitor_nD",
    ]


def test_instrument_name_and_parameters(build):
    inst = build({"name": "my_run", "gonio_omega": {"angle": 30}})
    assert inst.name == "my_run"
    params = {p.name: p.value for p in inst.parameters}
    assert params["omega"] == 30 and params["chi"] == 0
    assert params["wavelength"] == pytest.approx(2.417262, abs=1e-5)


def test_goniometer_rotation(build):
    chi = _components(build())["gonio_chi"]
    assert chi.ROTATED_data == [0, 0, "-chi"]
    assert chi.ROTATED_reference == "gonio_omega"


def test_overrides_reach_the_components(build):
    comps = _components(build({"slit1": {"size": 0.02}, "placements": {"slit1": {"at": [0, 0, 1.2]}}}))
    assert comps["slit1"].xwidth == 0.02
    assert comps["slit1"].AT_data == [0, 0, 1.2]
    assert comps["incident_monitor"].xwidth == 0.04  # twice the slit opening


def test_renamed_component_keeps_its_references(build):
    comps = _components(build({"source": {"name": "my_source"}}))
    assert "my_source" in comps and "source" not in comps
    assert comps["slit1"].AT_reference == "my_source"
    assert comps["slit1"].component_name == "Slit"


def test_build_from_a_yaml_path(build, write_yaml):
    assert build(write_yaml("name: example_run\n")).name == "example_run"


def test_the_sample_sets_the_crystal(tmp_path):
    from align_crystal.samples import la2ni7

    sample = la2ni7(mosaic=60)
    inst = build_instrument(load_config(), sample=sample, input_path=tmp_path)
    crystal = _components(inst)["crystal"]
    assert crystal.mosaic == 60
    assert sample.reflections in crystal.reflections
