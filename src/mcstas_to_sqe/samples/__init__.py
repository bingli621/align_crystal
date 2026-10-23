"""Ready-made samples, for any instrument.

Each function returns a :class:`.Single_crystal` with its own lattice and orientation, and its
CIF file (if any) in this folder. Placement is up to the caller: ``at``, and ``relative`` to a
component of the instrument, e.g. the diffractometer's ``"gonio_phi"``. Keyword arguments set
the crystal's other parameters or change the defaults, e.g.
``la2ni7(mosaic=60, at=[0, 0, 0], relative="gonio_phi")``.

``reflections`` names a CIF file relative to this folder (``CIF_DIR`` in
core/components/crystal.py), so a saved parameters file is portable.

To add a sample:

1. Put its CIF file in this folder (e.g. ``NaCl.cif``), or use a McStas built-in reflection list
   (e.g. ``"Al.lau"``), which needs no file.
2. Add a function like :func:`la2ni7`, with ``lattice_params``, ``along_beam``, ``in_plane``,
   ``reflections`` and any other ``Single_crystal`` value it needs (e.g. ``mosaic``), then
   ``**params`` last so a caller can change any of them.
3. Add its name to ``__all__``.
4. Add it to the loop of ``test_the_samples_are_crystals_placed_like_any_component``
   (tests/samples/test_samples.py).
"""

from typing import Any

from mcstas_to_sqe.core.components import Single_crystal

__all__ = ["aluminum", "la2ni7"]


def aluminum(**params: Any) -> Single_crystal:
    """Create an fcc aluminum crystal with cubic axes along the lab axes.

    Uses the McStas built-in reflection list Al.lau.

    Parameters
    ----------
    **params:
        Further ``Single_crystal`` parameters, or changes to the defaults (e.g. ``at``,
        ``relative``, ``mosaic``).

    Returns
    -------
    :
        The crystal.
    """
    return Single_crystal(
        **{
            "lattice_params": [4.0495, 4.0495, 4.0495, 90.0, 90.0, 90.0],
            "along_beam": [0, 0, 1],
            "in_plane": [1, 0, 0],
            "reflections": "Al.lau",
            **params,
        }
    )


def la2ni7(**params: Any) -> Single_crystal:
    """Create a La2Ni7 crystal (P6_3/mmc) with (001) along the beam.

    The structure is from La2Ni7.cif (COD 1523044). (1.357, 1, 0) lies in the horizontal plane,
    to the left of the beam.

    Parameters
    ----------
    **params:
        Further ``Single_crystal`` parameters, or changes to the defaults (e.g. ``at``,
        ``relative``, ``mosaic``).

    Returns
    -------
    :
        The crystal.
    """
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
