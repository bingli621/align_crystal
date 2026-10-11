"""The generic Instrument, with a small instrument of its own."""

import subprocess
import sys
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


class MemoryFormat:
    """A ConfigFormat that keeps the "files" in a dict: the entities work with any format."""

    def __init__(self, files):
        self.files = files

    def read(self, path):
        return self.files[str(path)]

    def write(self, data, path):
        self.files[str(path)] = data


@dataclass(kw_only=True)
class OneSlit(Instrument):
    PARAMS_FILE: ClassVar = "defaults"

    @classmethod
    def from_dict(cls, data):
        slit = Slit(**data["slit"], **data["placements"]["slit"])
        return cls(name=data["name"], components={"slit": slit})


DEFAULTS = {
    "name": "one_slit",
    "slit": {"size": 0.01},
    "placements": {"slit": {"at": [0, 0, 1], "rotated": None, "relative": None}},
}


def test_from_file_and_to_file_with_an_injected_format():
    fmt = MemoryFormat({"defaults": DEFAULTS, "mine": {"slit": {"size": 0.5}}})
    inst = OneSlit.from_file("mine", fmt)
    assert inst.slit.size == 0.5 and inst.slit.at == [0, 0, 1]  # default kept
    inst.to_file("out", fmt)
    assert fmt.files["out"]["slit"] == {"size": 0.5}
    assert OneSlit.from_file("out", fmt) == inst


def test_from_overrides_rejects_unknown_keys():
    fmt = MemoryFormat({"defaults": DEFAULTS})
    assert OneSlit.from_overrides({"slit": {"size": 2}}, fmt).slit.size == 2
    with pytest.raises(ValueError, match="slit.sizee"):
        OneSlit.from_overrides({"slit": {"sizee": 2}}, fmt)


def test_the_entities_do_not_import_a_file_format_or_the_outer_layers():
    """Dependency inversion: importing the instrument package loads no YAML and no file_io/mcstas."""
    code = (
        "import sys, align_crystal.instrument;"
        "bad = [m for m in sys.modules if m in ('yaml', 'json') or m.startswith(('align_crystal.file_io', 'align_crystal.mcstas'))];"
        "assert not bad, bad"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
