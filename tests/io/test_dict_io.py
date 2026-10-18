from align_crystal.instrument import Slit
from align_crystal.io.dict_io import components, merge

DATA = {
    "name": "tiny",
    "slit": {
        "component": "Slit",
        "xwidth": 0.5,
        "yheight": 0.5,
        "at": [0, 0, 1],
        "rotated": [0, 0, 0],
        "relative": None,
    },
}


def test_a_component_is_made_of_its_section_with_where_it_sits():
    slit = components(DATA, {"Slit": Slit})["slit"]
    assert (slit.xwidth, slit.at) == (0.5, [0, 0, 1])


def test_the_order_is_the_order_of_the_sections():
    data = {
        "b": {"component": "Slit", "xwidth": 1, "yheight": 1, "at": [0, 0, 0]},
        "name": "two",
        "a": {"component": "Slit", "xwidth": 2, "yheight": 2, "at": [0, 0, 1], "relative": "b"},
    }
    assert list(components(data, {"Slit": Slit})) == ["b", "a"]


def test_merge_lays_one_dict_over_another():
    base = {"a": {"x": 1, "y": 2}, "b": [1, 2]}
    assert merge(base, {"a": {"x": 5, "y": None}, "b": [3]}) == {"a": {"x": 5, "y": 2}, "b": [3]}
    assert base == {"a": {"x": 1, "y": 2}, "b": [1, 2]}  # not changed
