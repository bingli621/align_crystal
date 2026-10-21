"""The instruments, one package each: an `Instrument` (core/base.py) with its own
components, control parameters and reference parameters file. Importing this package adds every
one to INSTRUMENTS (io/ imports it, so a file can name any of them).

diffractometer/    SingleCrystalDiffractometer(sample, params); its Params, DEFAULT_PARAMS; and
                   PARAMS_FILE, its default saved (params.yaml)

To add an instrument: a package here like diffractometer/ (its class, a subclass of
`Instrument`, and its params.yaml), imported and exported below.
"""

from .diffractometer import DEFAULT_PARAMS, PARAMS_FILE, Params, SingleCrystalDiffractometer

__all__ = ["DEFAULT_PARAMS", "PARAMS_FILE", "Params", "SingleCrystalDiffractometer"]
