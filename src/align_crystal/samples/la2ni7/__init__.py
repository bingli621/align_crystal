"""La2Ni7 (P6_3/mmc), structure from La2Ni7.cif (COD 1523044)."""

from pathlib import Path

from align_crystal.samples.sample import oriented_sample

CIF = Path(__file__).parent / "La2Ni7.cif"


def la2ni7(mosaic=30.0):
    """La2Ni7: (001) along the beam, (1.357, 1, 0) in the horizontal plane to the left."""
    return oriented_sample(
        (5.0556, 5.0556, 24.5980, 90, 90, 120),
        CIF,
        (0, 0, 1),
        (1.357, 1, 0),
        mosaic,
    )
