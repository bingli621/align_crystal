"""The single-crystal diffractometer.

scd.py             SingleCrystalDiffractometer(sample, params), an Instrument: makes its own
                   components around the sample; its control parameters Params, DEFAULT_PARAMS;
                   instr_params: the wavelength of ei, and the goniometer angles
params.yaml        its default saved (PARAMS_FILE): a reference of how a parameters file looks
"""

from pathlib import Path

from .scd import DEFAULT_PARAMS, Params, SingleCrystalDiffractometer

PARAMS_FILE = Path(__file__).parent / "params.yaml"  # the default diffractometer saved: a reference

__all__ = ["DEFAULT_PARAMS", "PARAMS_FILE", "Params", "SingleCrystalDiffractometer"]
