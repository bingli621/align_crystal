"""Read McStas NeXus (HDF5) output, including mcrun scans, with mcstastox.

A scan file holds one entry per scan point (entry1, entry2, ...). This needs the mcstastox
branch with `entry_number` support (https://github.com/mads-bertelsen-agentic/McStasToX,
branch entry_choice).
"""

import mcstastox
from scippneutron.conversion.graph import beamline, tof
import numpy as np
import scipp as sc


def read_scan(folder, component="detector", source="source", sample="sample_pos"):
    """Return a list of (parameters, events) for each scan point.

    `parameters` is a dict of the instrument parameters of that point;
    `events` is a scipp DataArray over 'pixel_id' with the intensity summed per pixel and coords
    `position`, `pixel_id`, `gamma` [deg, signed in-plane scattering angle, negative to the right
    of the beam; not scippneutron's two_theta, which is the full angle between ki and kf] and `y` [m] (height above the sample). Only pixels that were hit are included.
    """
    points = []
    with mcstastox.Read(str(folder)) as data:
        n_entries = data.get_number_of_entries()

    for entry in range(1, n_entries + 1):
        with mcstastox.Read(str(folder), entry_number=entry) as data:
            params = {k: float(v) for k, v in data.get_instrument_parameters().items()}
            grouped = data.export_scipp(source, sample, component_name=component)[
                "events"
            ]
            sample_pos = data.get_global_component_coordinates(sample)

        pixels = grouped.bins.sum()  # events are grouped by pixel id; sum the weights
        x, y, z = (pixels.coords["position"].values - sample_pos).T
        pixels.coords["gamma"] = sc.array(
            dims=["pixel_id"], values=np.degrees(np.arctan2(x, z)), unit="deg"
        )
        pixels.coords["y"] = sc.array(dims=["pixel_id"], values=y, unit="m")
        points.append((params, pixels))
    return points


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
