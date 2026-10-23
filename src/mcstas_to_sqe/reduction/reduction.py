"""Momentum transfer in the lab and sample frames.

Works on the pixel DataArrays returned by :func:`mcstas_to_sqe.mcstas.nexus_io.read_scan`.
"""

from collections.abc import Mapping

import numpy as np
import scipp as sc
from scippneutron.conversion.graph import beamline, tof

from mcstas_to_sqe.core.geometry import rotation

# scippneutron graph: positions -> two_theta (angle between ki and kf) -> momentum transfer
Q_GRAPH = {
    **beamline.beamline(scatter=True),
    **tof.elastic_Q_vec("wavelength"),  # Qx, Qy, Qz, Q_vec
}


def wavelength(energy_meV: float) -> sc.Variable:
    """Convert a neutron energy to its wavelength.

    Parameters
    ----------
    energy_meV:
        Energy in meV, e.g. the diffractometer's ``params.ei``.

    Returns
    -------
    :
        Scalar wavelength in Å, ``sqrt(81.80421 / energy_meV)``.
    """
    return sc.scalar(float(np.sqrt(81.80421 / energy_meV)), unit="angstrom")


def run_wavelength(params: Mapping[str, float], given: sc.Variable | None = None) -> sc.Variable:
    """Return the wavelength of a scan point.

    Parameters
    ----------
    params:
        Instrument parameters of the scan point, as stored in the McStas output.
    given:
        Wavelength to use instead. If ``None``, the instrument parameter ``wavelength`` (Å).

    Returns
    -------
    :
        Scalar wavelength.
    """
    if given is not None:
        return given
    return sc.scalar(float(params["wavelength"]), unit="angstrom")


def to_Q(events: sc.DataArray, wavelength: sc.Variable) -> sc.DataArray:
    """Add the elastic momentum transfer.

    Uses scippneutron's conversion graph from the coords ``position``, ``sample_position`` and
    ``source_position``.

    Parameters
    ----------
    events:
        Pixels as returned by :func:`.read_scan`.
    wavelength:
        Scalar wavelength, e.g. ``wavelength(14)``.

    Returns
    -------
    :
        A shallow copy of ``events`` with the coords ``two_theta`` and ``Qx``, ``Qy``, ``Qz`` in
        1/Å, in the beam frame (z along ki, y up).
    """
    events = events.copy(deep=False)
    events.coords["wavelength"] = wavelength
    return events.transform_coords(["two_theta", "Qx", "Qy", "Qz"], graph=Q_GRAPH, keep_inputs=True)


def goniometer_matrix(omega: float, chi: float, phi: float) -> np.ndarray:
    """Compute the sample orientation in the lab frame, ``R = R_y(omega) R_-z(chi) R_x(phi)``.

    R is the inverse of the McStas rotations of the instrument's nested arms (omega about y
    outermost, then -z, then x), which go lab -> sample (see :func:`.geometry.rotation`).

    Parameters
    ----------
    omega, chi, phi:
        Goniometer angles in deg.

    Returns
    -------
    :
        (3, 3) matrix from the sample frame to the lab frame.
    """
    lab_to_sample = rotation(phi, 0, 0) @ rotation(0, 0, -chi) @ rotation(0, omega, 0)
    return lab_to_sample.T


def to_sample_frame(events: sc.DataArray, params: Mapping[str, float]) -> sc.DataArray:
    """Add Q in the sample frame, ``Q_sample = R^-1 Q_lab = R_x(-phi) R_z(chi) R_y(-omega) Q_lab``.

    Parameters
    ----------
    events:
        Pixels with the coords ``Qx``, ``Qy``, ``Qz``, from :func:`to_Q`.
    params:
        Instrument parameters with ``omega``, ``chi`` and ``phi`` in deg.

    Returns
    -------
    :
        A shallow copy of ``events`` with the coords ``Qx_sample``, ``Qy_sample``,
        ``Qz_sample`` in 1/Å.
    """
    R = goniometer_matrix(params["omega"], params["chi"], params["phi"])
    q_lab = np.stack([events.coords[k].values for k in ("Qx", "Qy", "Qz")])
    q_sample = R.T @ q_lab  # rotation matrices: inverse = transpose
    events = events.copy(deep=False)
    for name, values in zip(("Qx_sample", "Qy_sample", "Qz_sample"), q_sample):
        events.coords[name] = sc.array(dims=events.dims, values=values, unit="1/angstrom")
    return events
