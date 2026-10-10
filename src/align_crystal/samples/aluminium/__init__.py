"""Aluminium: fcc Al, the McStas built-in reflection list Al.lau."""

from align_crystal.samples.sample import oriented_sample


def aluminium(mosaic=5.0):
    """fcc Al, cubic axes along the lab axes."""
    return oriented_sample(
        (4.0495,) * 3 + (90,) * 3, "Al.lau", (0, 0, 1), (1, 0, 0), mosaic
    )
