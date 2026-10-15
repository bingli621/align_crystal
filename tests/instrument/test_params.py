import pytest

from align_crystal.instrument import DesignParam, InstrumentParam, Slit

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


def test_make_takes_the_section_with_where_it_sits():
    slit = DesignParam(DATA).make(Slit, "slit")
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
def test_make_components_rejects_unknown_things(changes, match):
    with pytest.raises(ValueError, match=match):
        DesignParam({**DATA, **changes}).make_components({"Slit": Slit})


def test_a_key_that_is_not_a_section_raises():
    with pytest.raises(TypeError, match="Unknown config key: extra"):
        DesignParam({**DATA, "extra": 1}).make_components({"Slit": Slit})


def test_the_order_is_the_order_of_the_sections():
    data = {
        "b": {"component": "Slit", "xwidth": 1, "yheight": 1, "at": [0, 0, 0]},
        "name": "two",
        "a": {"component": "Slit", "xwidth": 2, "yheight": 2, "at": [0, 0, 1], "relative": "b"},
    }
    assert list(DesignParam(data).make_components({"Slit": Slit})) == ["b", "a"]


def test_instrument_param_replaces_values_and_rejects_unknown_names():
    instrument_params = InstrumentParam({"omega": 0.0}, {"omega": "deg"}, {"omega": ""})
    assert (
        instrument_params.replace(omega=30)["omega"] == 30 and instrument_params["omega"] == 0.0
    )  # a copy
    with pytest.raises(ValueError, match="Unknown instrument parameter.*omgea"):
        instrument_params.replace(omgea=30)


def test_complete_raises_on_a_control_that_is_not_set():
    instrument_params = InstrumentParam({"e": None, "omega": 0.0}, {}, {})
    with pytest.raises(ValueError, match="not set: e$"):
        instrument_params.complete()
    assert instrument_params.replace(e=14).complete()["e"] == 14


def test_from_parameters_makes_the_same_as_the_controls_section():
    from align_crystal.instrument import InstrumentParameter

    made = InstrumentParam.from_parameters(
        a=InstrumentParameter(None, "m", "length"), b=InstrumentParameter(1.0)
    )
    assert made == InstrumentParam.from_dict(
        {"a": {"value": None, "unit": "m", "comment": "length"}, "b": {"value": 1.0}}
    )
