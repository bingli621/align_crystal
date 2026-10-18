"""Data reduction: momentum transfer in the lab and sample frames.

Works on the pixel DataArrays returned by `align_crystal.mcstas.h5_reader.read_scan`.
"""

import numpy as np
import scipp as sc
from scippneutron.conversion.graph import beamline, tof

from align_crystal.instrument.geometry import rotation

# scippneutron graph: positions -> two_theta (angle between ki and kf) -> momentum transfer
Q_GRAPH = {
    **beamline.beamline(scatter=True),
    **tof.elastic_Q_vec("wavelength"),  # Qx, Qy, Qz, Q_vec
}


def wavelength(energy_meV):
    """The neutron wavelength of `energy_meV` (e.g. the diffractometer's `params.ei`), as a scipp
    scalar in angstrom: lambda[A] = sqrt(81.80421 / E[meV])."""
    return sc.scalar(float(np.sqrt(81.80421 / energy_meV)), unit="angstrom")


def run_wavelength(params, given=None):
    """The wavelength of a scan point, as a scipp scalar: `given` if not None, else the instrument
    parameter `wavelength` (angstrom) stored in the McStas output (`params`, its parameters)."""
    if given is not None:
        return given
    return sc.scalar(float(params["wavelength"]), unit="angstrom")


def to_Q(events, wavelength):
    """Add elastic momentum transfer to `events` (as returned by `read_scan`).

    `wavelength` is a scipp scalar (e.g. `wavelength(14)`). Uses
    scippneutron's graph from the detector positions (`position`, `sample_position`,
    `source_position`): returns a DataArray with coords two_theta, Qx, Qy, Qz [1/angstrom],
    in the beam frame (z along ki, y up).
    """
    events = events.copy(deep=False)
    events.coords["wavelength"] = wavelength
    return events.transform_coords(["two_theta", "Qx", "Qy", "Qz"], graph=Q_GRAPH, keep_inputs=True)


def goniometer_matrix(omega, chi, phi):
    """Sample orientation in the lab frame (deg): R = R_y(omega) R_-z(chi) R_x(phi).

    Made of the McStas rotations of the nested arms of the instrument (omega about Y outermost,
    then -Z, then X), which go lab -> sample (`instrument.geometry.rotation`): R is their inverse.
    """
    lab_to_sample = rotation(phi, 0, 0) @ rotation(0, 0, -chi) @ rotation(0, omega, 0)
    return lab_to_sample.T


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
