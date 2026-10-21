from align_crystal.instrument import Params, SingleCrystalDiffractometer
from align_crystal.mcstas.simulation import Simulation


class _Inst:
    def set_parameters(self, **values):
        self.values = values


def test_a_run_gives_its_own_values_in_place_of_the_diffractometers():
    inst = _Inst()
    sim = Simulation(SingleCrystalDiffractometer(params=Params(omega=30)))
    scans = sim._set_instr_params(inst, {"chi": 1, "phi": "0,5"})
    assert inst.values["omega"] == 30 and inst.values["chi"] == 1  # the diffractometer's, the run's
    assert scans == {"phi": "0,5"}  # a scan range is returned, not set
    Simulation(SingleCrystalDiffractometer())._set_instr_params(inst, {"wavelength": 3.0})
    assert inst.values["wavelength"] == 3.0  # a run may set it
