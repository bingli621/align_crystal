from pathlib import Path

import pytest

from mcstas_to_sqe.instruments import Params, SingleCrystalDiffractometer
from mcstas_to_sqe.mcstas.simulation import Simulation


def test_a_run_gives_its_own_values_in_place_of_the_diffractometers():
    sim = Simulation(SingleCrystalDiffractometer(params=Params(omega=30)))
    values = sim._get_params({"chi": 1, "wavelength": 3.0})
    assert values["omega"] == 30 and values["chi"] == 1  # the diffractometer's, the run's
    assert values["wavelength"] == 3.0  # a run may set it


def test_a_scan_has_a_run_per_value_of_its_variable():
    points = Simulation(SingleCrystalDiffractometer())._points("omega", range(3), {"chi": 4})
    assert [(p["omega"], p["chi"], p["phi"]) for p in points] == [(0, 4, 0), (1, 4, 0), (2, 4, 0)]


@pytest.mark.parametrize("instr_params", [{"omega": "3,5"}, {"omega": [1, 2]}, {"omgea": 3}])
def test_a_run_takes_one_number_per_known_parameter(instr_params):
    with pytest.raises(ValueError):
        Simulation(SingleCrystalDiffractometer())._get_params(instr_params)


def test_a_scan_of_an_unknown_variable_raises():
    with pytest.raises(ValueError, match="omgea"):
        Simulation(SingleCrystalDiffractometer())._points("omgea", [1, 2], {})


def test_the_folders_are_in_the_work_folder(tmp_path, monkeypatch):
    monkeypatch.delenv("MCSTAS_TO_SQE_WORKDIR", raising=False)
    monkeypatch.chdir(tmp_path)
    d = SingleCrystalDiffractometer()
    sim = Simulation(d)
    assert sim.output_dir == tmp_path / "mcstas_output"
    assert sim.input_dir == tmp_path / "mcstas_input" / d.name
    sim = Simulation(d, work_dir=tmp_path / "w", output_dir="out")
    assert (
        sim.output_dir == Path("out") and sim.input_dir == tmp_path / "w" / "mcstas_input" / d.name
    )


def test_the_beam_file_is_the_newest_one_found(tmp_path, finished_run):
    assert Simulation(SingleCrystalDiffractometer(), output_dir=tmp_path).beam_file is None
    finished_run(tmp_path / "old_beam", 1, beam=True)
    new = finished_run(tmp_path / "new_beam", 2, beam=True)
    finished_run(tmp_path / "newer_scan", 3)
    sim = Simulation(SingleCrystalDiffractometer(), output_dir=tmp_path)
    assert sim.beam_file == new / "beam.mcpl.gz"
