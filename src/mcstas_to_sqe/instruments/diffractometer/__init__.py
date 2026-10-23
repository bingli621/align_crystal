"""The single-crystal diffractometer, and its default saved as params.yaml (``PARAMS_FILE``)."""

from pathlib import Path

from .scd import DEFAULT_PARAMS, Params, SingleCrystalDiffractometer

PARAMS_FILE = Path(__file__).parent / "params.yaml"  # the default diffractometer saved: a reference

__all__ = ["DEFAULT_PARAMS", "PARAMS_FILE", "Params", "SingleCrystalDiffractometer"]
