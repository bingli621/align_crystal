"""The generic Instrument: it takes and gives plain dicts, and knows no file."""

import copy
import subprocess
import sys

import pytest

from align_crystal.core import Instrument, Slit

DATA = {
    "name": "tiny",
    "components": {"slit": "Slit"},
    "slit": {"size": 1},
    "placements": {"slit": {"at": [0, 0, 1], "rotated": None, "relative": None}},
}


def test_from_params_keys_the_components_by_role_in_order():
    b = Slit(size=2, at=[0, 0, 0])
    a = Slit(size=1, at=[0, 0, 1], relative="b")
    inst = Instrument.from_params("x", b=b, a=a)
    assert list(inst.components) == ["b", "a"] and inst.a is a
    assert (a.name, b.name) == ("a", "b")  # the role, since no name was given


def test_from_dict_then_to_dict_roundtrip():
    inst = Instrument.from_dict(DATA)
    assert list(inst.components) == ["slit"] and inst.slit.size == 1
    assert Instrument.from_dict(inst.to_dict()) == inst
    assert inst.to_dict()["components"] == {"slit": "Slit"}


def test_from_file_reads_the_file_with_the_loader_it_is_given():
    seen = []

    def loader(file):
        seen.append(file)
        return copy.deepcopy(DATA)

    inst = Instrument.from_file("any.thing", loader)
    assert seen == ["any.thing"] and inst == Instrument.from_dict(DATA)
    with pytest.raises(TypeError):  # the entities know no format: a loader is always needed
        Instrument.from_file("any.thing")


def test_a_null_that_cannot_be_derived_raises():
    with pytest.raises(ValueError, match="slit.size"):
        Instrument.from_params("x", slit=Slit(size=None, at=[0, 0, 0]))


def test_core_imports_no_yaml_and_no_adapter():
    """Dependency inversion: the entities know no file format and no adapter."""
    code = (
        "import sys, align_crystal.core;"
        "bad = [m for m in sys.modules if m == 'yaml' or m.startswith(('align_crystal.yaml_io', 'align_crystal.mcstas'))];"
        "assert not bad, bad"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_the_library_does_not_import_the_instruments_folder():
    """instruments/ is outside the package: nothing in align_crystal may depend on it."""
    code = (
        "import sys, align_crystal.core, align_crystal.mcstas.builder, align_crystal.mcstas.simulater, "
        "align_crystal.reduction, align_crystal.yaml_io;"
        "assert 'instruments' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
