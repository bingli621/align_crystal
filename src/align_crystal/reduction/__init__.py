"""Data reduction: momentum transfer, sample frame, solid-angle normalization, peak finding."""

from .normalization import (
    detector_solid_angle,
    incident_intensity,
    normalize_scan,
)
from .peaks import Peak, centre_of_mass, find_peaks
from .reduction import goniometer_matrix, to_Q, to_sample_frame, wavelength
from .solid_angle import rectangle_solid_angle

__all__ = [
    "Peak",
    "centre_of_mass",
    "detector_solid_angle",
    "goniometer_matrix",
    "find_peaks",
    "incident_intensity",
    "normalize_scan",
    "rectangle_solid_angle",
    "to_Q",
    "to_sample_frame",
    "wavelength",
]
