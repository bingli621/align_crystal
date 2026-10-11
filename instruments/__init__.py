"""The instruments of this project: concrete instruments built from the generic entities of
`align_crystal.core`. This folder is outside the library package (it is not installed with it): it
is the project's own content, like `scripts/`, and it is imported from the repository root
(pytest and pixi put that on the path).

single_crystal_diffractometer/   a plain folder (no __init__.py), one per instrument:
    diffractometer.py   SingleCrystalDiffractometer, an `Instrument` with its own rule for the source
                        focus, and the ways to create it: from_dict, from_file, from_parameters
    params.yaml         its complete parameters file; it names its components in beam order
"""

from .single_crystal_diffractometer.diffractometer import SingleCrystalDiffractometer

__all__ = ["SingleCrystalDiffractometer"]
