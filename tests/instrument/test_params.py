from align_crystal.instrument import InstrParam, with_values


def test_with_values_replaces_values():
    params = [InstrParam("omega", 0.0, "deg")]
    assert with_values(params, omega=30)[0].value == 30 and params[0].value == 0.0  # a copy
