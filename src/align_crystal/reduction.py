"""Data reduction: momentum transfer in the lab and sample frames.

Works on the pixel DataArrays returned by `align_crystal.io.read_scan`.
"""

import numpy as np
import scipp as sc
from scippneutron.conversion.graph import beamline, tof


# scippneutron graph: positions -> two_theta (angle between ki and kf) -> momentum transfer
Q_GRAPH = {
    **beamline.beamline(scatter=True),
    **tof.elastic_Q_vec("wavelength"),  # Qx, Qy, Qz, Q_vec
}


def to_Q(events, wavelength):
    """Add elastic momentum transfer to `events` (as returned by `read_scan`).

    `wavelength` is a scipp scalar (e.g. sc.scalar(2.417262, unit="angstrom")). Uses
    scippneutron's graph from the detector positions (`position`, `sample_position`,
    `source_position`): returns a DataArray with coords two_theta, Qx, Qy, Qz [1/angstrom],
    in the beam frame (z along ki, y up).
    """
    events = events.copy(deep=False)
    events.coords["wavelength"] = wavelength
    return events.transform_coords(
        ["two_theta", "Qx", "Qy", "Qz"], graph=Q_GRAPH, keep_inputs=True
    )


def _rot(axis, angle_deg):
    """Right-handed (active) rotation matrix about +x, +y or +z."""
    a = np.radians(angle_deg)
    c, s = np.cos(a), np.sin(a)
    return {
        "x": np.array([[1, 0, 0], [0, c, -s], [0, s, c]]),
        "y": np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]]),
        "z": np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]]),
    }[axis]


def goniometer_matrix(omega, chi, phi):
    """Sample orientation in the lab frame (deg): R = R_y(omega) R_-z(chi) R_x(phi).

    Matches the nested McStas arms of the instrument (omega about Y outermost, then -Z, then X);
    McStas stores the inverse of this (lab -> sample) as the crystal's `Rotation`.
    """
    return _rot("y", omega) @ _rot("z", -chi) @ _rot("x", phi)


def to_sample_frame(events, params):
    """Add Q in the sample frame: Q_sample = R^-1 Q_lab = R_x(-phi) R_z(chi) R_y(-omega) Q_lab.

    `events` must have Qx, Qy, Qz (from `to_Q`); `params` holds omega, chi and phi (deg).
    Adds coords Qx_sample, Qy_sample, Qz_sample [1/angstrom].
    """
    R = goniometer_matrix(params["omega"], params["chi"], params["phi"])
    q_lab = np.stack([events.coords[k].values for k in ("Qx", "Qy", "Qz")])
    q_sample = R.T @ q_lab  # rotation matrices: inverse = transpose
    events = events.copy(deep=False)
    for name, values in zip(("Qx_sample", "Qy_sample", "Qz_sample"), q_sample):
        events.coords[name] = sc.array(dims=events.dims, values=values, unit="1/angstrom")
    return events
