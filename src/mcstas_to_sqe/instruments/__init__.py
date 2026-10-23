"""The instruments, one package each.

Each is an :class:`.Instrument` subclass with its own components, control parameters and
reference parameters file. Importing this package adds every instrument to ``INSTRUMENTS``; io/
imports it, so a file can name any of them.

To add an instrument, add a package here like diffractometer/, with its class and its
params.yaml, and import and export it below.
"""

from .diffractometer import DEFAULT_PARAMS, PARAMS_FILE, Params, SingleCrystalDiffractometer

__all__ = ["DEFAULT_PARAMS", "PARAMS_FILE", "Params", "SingleCrystalDiffractometer"]
