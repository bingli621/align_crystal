"""The generic Instrument, with a small instrument of its own."""

from dataclasses import dataclass
from typing import ClassVar

import pytest

from align_crystal.file_io import load_config
from align_crystal.instrument import Diffractometer, Instrument, Slit


@pytest.fixture
def Tiny(write_yaml):
    """An instrument with one slit, whose size defaults to twice its distance."""
    params = write_yaml(
        "name: tiny\n"
        "slit:\n  size: null\n"
        "placements:\n  slit: {at: [0, 0, 1], rotated: null, relative: null}\n",
        name="tiny.yaml",
    )

    @dataclass(kw_only=True)
    class Tiny(Instrument):
        PARAMS_FILE: ClassVar = params

        @classmethod
        def from_dict(cls, data):
            slit = Slit(**data["slit"], **data["placements"]["slit"])
            return cls(name=data["name"], components={"slit": slit})

        def __post_init__(self):
            if self.slit.size is None:
                self.slit.size = 2 * self.slit.at[2]
            super().__post_init__()

    return Tiny


def test_another_kind_of_instrument(Tiny):
    inst = load_config({"name": "mine"}, cls=Tiny)
    assert isinstance(inst, Tiny) and not isinstance(inst, Diffractometer)
    assert inst.name == "mine" and inst.slit.size == 2
    assert set(inst.components) == {"slit"}


def test_derivation_follows_the_overrides(Tiny):
    cfg = load_config({"placements": {"slit": {"at": [0, 0, 3]}}}, cls=Tiny)
    assert cfg.slit.size == 6


def test_a_base_instrument_cannot_build_itself():
    with pytest.raises(NotImplementedError):
        Instrument.from_dict({})
