import pytest

from align_crystal.core import ControlParam, DesignParam, Slit

DATA = {
    "name": "tiny",
    "slit": {"component": "Slit", "size": 0.5, "at": [0, 0, 1], "rotated": None, "relative": None},
}


def test_make_takes_the_section_with_where_it_sits():
    slit = DesignParam(DATA).make(Slit, "slit")
    assert (slit.size, slit.at) == (0.5, [0, 0, 1])


@pytest.mark.parametrize(
    "changes, match",
    [
        ({"extra": 1}, "Unknown config key: extra"),
        ({"slit": {"size": 0.5, "at": [0, 0, 1]}}, "No component in the section of 'slit'"),
        ({"slit": {"component": "Nope"}}, "Unknown component 'Nope'"),
        ({"slit": {"component": "Slit", "sizee": 1, "at": [0, 0, 1]}}, "slit.*sizee"),
        ({"slit": {"component": "Slit", "size": 0.5}}, "slit.*'at'"),
    ],
)
def test_make_components_rejects_unknown_things(changes, match):
    with pytest.raises(ValueError, match=match):
        DesignParam({**DATA, **changes}).make_components({"Slit": Slit})


def test_the_order_is_the_order_of_the_sections():
    data = {
        "b": {"component": "Slit", "size": 1, "at": [0, 0, 0]},
        "name": "two",
        "a": {"component": "Slit", "size": 2, "at": [0, 0, 1], "relative": "b"},
    }
    assert list(DesignParam(data).make_components({"Slit": Slit})) == ["b", "a"]


def test_control_param_replaces_values_and_rejects_unknown_names():
    controls = ControlParam({"omega": 0.0}, {"omega": "deg"}, {"omega": ""})
    assert controls.replace(omega=30)["omega"] == 30 and controls["omega"] == 0.0  # a copy
    with pytest.raises(ValueError, match="Unknown control parameter.*omgea"):
        controls.replace(omgea=30)


def test_complete_raises_on_a_control_that_is_not_set():
    controls = ControlParam({"e": None, "omega": 0.0}, {}, {})
    with pytest.raises(ValueError, match="not set: e$"):
        controls.complete()
    assert controls.replace(e=14).complete()["e"] == 14


def test_from_controls_makes_the_same_as_the_controls_section():
    from align_crystal.core import Control

    made = ControlParam.from_controls(a=Control(None, "m", "length"), b=Control(1.0))
    assert made == ControlParam.from_dict(
        {"a": {"value": None, "unit": "m", "comment": "length"}, "b": {"value": 1.0}}
    )
