import pytest

from align_crystal.core import Param, Slit

DATA = {
    "name": "tiny",
    "components": {"slit": "Slit"},
    "slit": {"size": 0.5},
    "placements": {"slit": {"at": [0, 0, 1], "rotated": None, "relative": None}},
}


def test_make_joins_the_section_and_the_placement_and_names_by_the_role():
    slit = Param(DATA).make(Slit, "slit")
    assert (slit.size, slit.at, slit.name) == (0.5, [0, 0, 1], "slit")


@pytest.mark.parametrize(
    "changes, match",
    [
        ({"extra": {}}, "Unknown config key: extra"),
        ({"placements": {**DATA["placements"], "other": {}}}, "placements.other"),
        ({"components": {"slit": "Nope"}}, "Unknown component 'Nope'"),
        ({"slit": {"sizee": 1}}, "slit.*sizee"),
    ],
)
def test_make_components_rejects_unknown_things(changes, match):
    with pytest.raises(ValueError, match=match):
        Param({**DATA, **changes}).make_components({"Slit": Slit})
