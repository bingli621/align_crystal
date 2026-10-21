"""Ready-made samples, for any instrument: each function gives a `Single_crystal` of its own
lattice and orientation, with its CIF file (if any) in this folder. Where it sits is the caller's:
`at`, and `relative`, a component of the instrument (e.g. the diffractometer's "gonio_phi").

`params` are the crystal's other parameters, or ones to change, e.g.
`la2ni7(mosaic=60, at=[0, 0, 0], relative="gonio_phi")`. `reflections` names a CIF file relative to
this folder (`CIF_DIR` of core/components/crystal.py), so a saved parameters file is portable.

To add a sample:
1. Put its CIF file in this folder (e.g. `NaCl.cif`), or use a McStas built-in reflection list
   (e.g. "Al.lau"), which needs no file.
2. Add a function here like `la2ni7` below: its `lattice_params` (a, b, c in angstrom; alpha, beta,
   gamma in deg), the reciprocal vector `along_beam` (hkl along the beam when all goniometer angles
   are zero), `in_plane` (hkl in the horizontal plane, towards +x), `reflections` (the file name),
   and any other `Single_crystal` value it needs (e.g. `mosaic`), then `**params` last so a caller
   can change any of them.
3. Add its name to `__all__` below.
4. Add it to the loop of `test_the_samples_are_crystals_placed_like_any_component`
   (tests/samples/test_samples.py).
"""

from ..core.components import Single_crystal

__all__ = ["aluminum", "la2ni7"]


def aluminum(**params) -> Single_crystal:
    """fcc Al, the McStas built-in reflection list Al.lau; cubic axes along the lab axes."""
    return Single_crystal(
        **{
            "lattice_params": [4.0495, 4.0495, 4.0495, 90.0, 90.0, 90.0],
            "along_beam": [0, 0, 1],
            "in_plane": [1, 0, 0],
            "reflections": "Al.lau",
            **params,
        }
    )


def la2ni7(**params) -> Single_crystal:
    """La2Ni7 (P6_3/mmc), structure from La2Ni7.cif (COD 1523044): (001) along the beam,
    (1.357, 1, 0) in the horizontal plane to the left."""
    return Single_crystal(
        **{
            "lattice_params": [5.0556, 5.0556, 24.5980, 90.0, 90.0, 120.0],
            "along_beam": [0, 0, 1],
            "in_plane": [1.357, 1, 0],
            "reflections": "La2Ni7.cif",
            "mosaic": 30.0,
            **params,
        }
    )
