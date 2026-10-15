import pytest

from align_crystal.instrument import InstrParam, Slit
from align_crystal.io.dict_io import components, instr_params_from_dict, merge

DATA = {
    "name": "tiny",
    "slit": {
        "component": "Slit",
        "xwidth": 0.5,
        "yheight": 0.5,
        "at": [0, 0, 1],
        "rotated": None,
        "relative": None,
    },
}


def test_a_component_is_made_of_its_section_with_where_it_sits():
    slit = components(DATA, {"Slit": Slit})["slit"]
    assert (slit.xwidth, slit.at) == (0.5, [0, 0, 1])


@pytest.mark.parametrize(
    "changes, match",
    [
        (
            {"slit": {"xwidth": 0.5, "yheight": 0.5, "at": [0, 0, 1]}},
            "No component in the section of 'slit'",
        ),
        ({"slit": {"component": "Nope"}}, "Unknown component 'Nope'"),
        ({"slit": {"component": "Slit", "sizee": 1, "at": [0, 0, 1]}}, "slit.*sizee"),
        ({"slit": {"component": "Slit", "xwidth": 0.5, "yheight": 0.5}}, "slit.*'at'"),
    ],
)
def test_components_rejects_unknown_things(changes, match):
    with pytest.raises(ValueError, match=match):
        components({**DATA, **changes}, {"Slit": Slit})


def test_a_key_that_is_not_a_section_raises():
    with pytest.raises(TypeError, match="Unknown config key: extra"):
        components({**DATA, "extra": 1}, {"Slit": Slit})


def test_the_order_is_the_order_of_the_sections():
    data = {
        "b": {"component": "Slit", "xwidth": 1, "yheight": 1, "at": [0, 0, 0]},
        "name": "two",
        "a": {"component": "Slit", "xwidth": 2, "yheight": 2, "at": [0, 0, 1], "relative": "b"},
    }
    assert list(components(data, {"Slit": Slit})) == ["b", "a"]


def test_an_instr_params_section_is_read_and_checked():
    params = instr_params_from_dict(
        {"a": {"value": None, "unit": "m", "comment": "length"}, "b": {"value": 1.0}}
    )
    assert params == [InstrParam("a", None, "m", "length"), InstrParam("b", 1.0)]
    with pytest.raises(ValueError, match="instr_params.a needs a value"):
        instr_params_from_dict({"a": {"unit": "m"}})
    with pytest.raises(ValueError, match="instr_params.a.units"):
        instr_params_from_dict({"a": {"value": 1, "units": "m"}})


def test_merge_lays_one_dict_over_another():
    base = {"a": {"x": 1, "y": 2}, "b": [1, 2]}
    assert merge(base, {"a": {"x": 5, "y": None}, "b": [3]}) == {"a": {"x": 5, "y": 2}, "b": [3]}
    assert base == {"a": {"x": 1, "y": 2}, "b": [1, 2]}  # not changed
