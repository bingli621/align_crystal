import pytest

from mcstas_to_sqe.instruments import Params, SingleCrystalDiffractometer
from mcstas_to_sqe.mcstas.simulation import Simulation


def test_a_run_gives_its_own_values_in_place_of_the_diffractometers():
    sim = Simulation(SingleCrystalDiffractometer(params=Params(omega=30)))
    values = sim._values({"chi": 1, "wavelength": 3.0})
    assert values["omega"] == 30 and values["chi"] == 1  # the diffractometer's, the run's
    assert values["wavelength"] == 3.0  # a run may set it


def test_a_scan_has_a_run_per_value_of_its_variable():
    points = Simulation(SingleCrystalDiffractometer())._points("omega", range(3), {"chi": 4})
    assert [(p["omega"], p["chi"], p["phi"]) for p in points] == [(0, 4, 0), (1, 4, 0), (2, 4, 0)]


@pytest.mark.parametrize("instr_params", [{"omega": "3,5"}, {"omega": [1, 2]}, {"omgea": 3}])
def test_a_run_takes_one_number_per_known_parameter(instr_params):
    with pytest.raises(ValueError):
        Simulation(SingleCrystalDiffractometer())._values(instr_params)


def test_a_scan_of_an_unknown_variable_raises():
    with pytest.raises(ValueError, match="omgea"):
        Simulation(SingleCrystalDiffractometer())._points("omgea", [1, 2], {})
