from dataclasses import dataclass
from pathlib import Path

import pytest

from align_crystal.instrument import (
    Instrument,
    Monitor,
    Progress_bar,
    SingleCrystalDiffractometer,
    Slit,
    la2ni7,
)
from align_crystal.mcstas import adapters
from align_crystal.mcstas.builder import build


def test_components_are_added_in_order_with_their_mcstas_names(tmp_path, diffractometer):
    inst = build(diffractometer(), input_path=tmp_path)
    assert [c.name for c in inst.component_list] == list(diffractometer().components)
    assert [c.component_name for c in inst.component_list] == [
        "Progress_bar", "Source_simple", "Slit", "Monitor", "Arm",
        "Arm", "Arm", "Arm", "Single_crystal", "Monitor_nD",
    ]  # fmt: skip


def test_the_parameters_and_the_goniometer_rotations(tmp_path, diffractometer):
    inst = build(diffractometer(), input_path=tmp_path)
    params = {p.name: p.value for p in inst.parameters}
    assert list(params) == ["wavelength", "omega", "chi", "phi"]  # the instrument parameters
    assert params["omega"] == 0  # the default, unless a run gives its own
    assert params["wavelength"] == pytest.approx(2.417262, abs=1e-5)  # calculated from ei = 14 meV
    source = next(c for c in inst.component_list if c.name == "source")
    assert source.lambda0 == "wavelength"  # the instrument parameter
    assert source.dlambda == 0 and source.E0 is None  # E0 unset: McStas uses lambda0
    chi = next(c for c in inst.component_list if c.name == "gonio_chi")
    assert chi.ROTATED_data == [0, 0, "-chi"] and chi.ROTATED_reference == "gonio_omega"


def test_the_source_focuses_at_the_distance_of_its_focus_on(tmp_path, diffractometer):
    d = diffractometer()
    source = next(c for c in build(d, input_path=tmp_path).component_list if c.name == "source")
    assert source.dist == pytest.approx(2.0)  # source -> sample_pos
    d.sample_pos.at = [0, 0, 0.6]  # a change is followed: 0.6 m after the monitor, at 1.9 m
    source = next(c for c in build(d, input_path=tmp_path).component_list if c.name == "source")
    assert source.dist == pytest.approx(2.5)


def test_the_sample_of_the_diffractometer_sets_the_mcstas_crystal(tmp_path):
    sample = la2ni7(mosaic=60, at=[0, 0, 0], relative="gonio_phi")
    cfg = SingleCrystalDiffractometer(sample)
    inst = build(cfg, input_path=tmp_path)
    crystal = next(c for c in inst.component_list if c.name == "sample")
    assert crystal.mosaic == 60 and cfg.sample.reflections in crystal.reflections
    assert Path(
        crystal.reflections.strip('"')
    ).is_absolute()  # McStas gets the full path of the CIF
    assert crystal.xwidth == cfg.sample.xwidth


@dataclass(frozen=True)
class _NoParams:
    pass


class _SlitOnly(Instrument):
    """Another instrument: the builder takes it unchanged."""

    params_class = _NoParams
    name = "slit_only"

    def __init__(self, params=None):
        super().__init__(params)
        self.origin = Progress_bar(at=[0, 0, 0])
        self.slit = Slit(xwidth=0.02, yheight=0.03, at=[0, 0, 1.0], relative="origin")
        self.monitor = Monitor(
            xwidth=0.04, yheight=0.05, restore_neutron=1, at=[0, 0, 0.5], relative="slit"
        )

    @property
    def instr_params(self):
        return []


def test_another_instrument_is_built_from_its_components_alone(tmp_path):
    inst = build(_SlitOnly(), input_path=tmp_path)
    assert [c.name for c in inst.component_list] == ["origin", "slit", "monitor"]
    slit, monitor = inst.component_list[1:]
    assert (slit.xwidth, slit.yheight) == (0.02, 0.03)  # the fields of the McStas parameters
    assert monitor.restore_neutron == 1  # its own field
    assert (monitor.xwidth, monitor.yheight) == (0.04, 0.05)  # its own fields


@dataclass(kw_only=True, repr=False)
class _GappedSlit(Slit):
    gap: float = 0.1  # no McStas parameter, and its adapter does not handle it


_GappedSlit.__name__ = "Slit"  # still the McStas Slit


def test_a_field_nothing_takes_raises(tmp_path):
    d = _SlitOnly()
    d.slit = _GappedSlit(xwidth=0.02, yheight=0.03, at=[0, 0, 1.0], relative="origin")
    with pytest.raises(ValueError, match=r"slit \(Slit\): no McStas parameter \['gap'\]"):
        build(d, input_path=tmp_path)


def test_an_adapter_value_mcstas_does_not_know_raises(tmp_path, monkeypatch):
    monkeypatch.setitem(adapters.ADAPTERS, Monitor, (lambda *_: {"bogus": 1}, set()))
    with pytest.raises(ValueError, match=r"monitor \(Monitor\): no McStas parameter \['bogus'\]"):
        build(_SlitOnly(), input_path=tmp_path)


def test_a_component_without_an_adapter_passes_its_fields_through():
    slit = Slit(xwidth=1, yheight=2, at=[0, 0, 0])
    assert Slit not in adapters.ADAPTERS
    assert adapters.mcstas_values(slit, "s", None) == {"xwidth": 1, "yheight": 2}


def test_the_source_focuses_on_a_component_of_the_instrument(tmp_path, diffractometer):
    d = diffractometer()
    d.source.focus_on = "nowhere"
    with pytest.raises(ValueError, match="source: focus_on 'nowhere' is no component"):
        build(d, input_path=tmp_path)


def test_an_adapter_that_sets_a_field_raises(monkeypatch):
    monkeypatch.setitem(adapters.ADAPTERS, Slit, (lambda *_: {"xwidth": 9}, set()))
    slit = Slit(xwidth=1, yheight=2, at=[0, 0, 0])
    with pytest.raises(ValueError, match=r"s \(Slit\): its adapter sets its fields \['xwidth'\]"):
        adapters.mcstas_values(slit, "s", None)
