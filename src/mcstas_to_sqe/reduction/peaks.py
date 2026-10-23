"""Peak list from the normalized events in sample-frame Q space.

Every detector pixel hit in every scan point is one point in (Qx, Qy, Qz)_sample, with the
normalized weight ``w = sum(p) / (I0 * solid_angle)`` in 1/sr. Peaks are connected regions of
high density in this point cloud. A peak's position is the centre of mass of the weights in its
region. Its uncertainties are propagated from the Monte Carlo statistics of the events and from
the incident-monitor uncertainty of each scan point.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import scipp as sc
from scipy import ndimage
from scipy.spatial import cKDTree

from .normalization import normalize_scan
from .reduction import run_wavelength, to_Q, to_sample_frame


@dataclass
class Peak:
    """A peak in sample-frame Q space.

    Parameters
    ----------
    q:
        (3,) centre of mass (Qx, Qy, Qz) in 1/Å.
    q_cov:
        (3, 3) covariance of ``q``.
    intensity:
        Integrated intensity in 1/sr, summed over the scan points (not divided by the scan
        step).
    intensity_err:
        Uncertainty of ``intensity``.
    n_points:
        Number of pixel contributions (over all scan points) in the peak.
    """

    q: np.ndarray
    q_cov: np.ndarray
    intensity: float
    intensity_err: float
    n_points: int

    @property
    def q_err(self) -> np.ndarray:
        """(3,) standard uncertainty of ``q``, in 1/Å."""
        return np.sqrt(np.diag(self.q_cov))


def load_points(
    folder: str | Path, wavelength: sc.Variable | None = None, **kwargs: Any
) -> dict[str, np.ndarray]:
    """Load a normalized scan as a point cloud in sample-frame Q space.

    Parameters
    ----------
    folder:
        Run folder with the ``mccode.h5`` of the scan.
    wavelength:
        Scalar wavelength for every scan point, e.g. from :func:`.wavelength`. If ``None``, the
        wavelength each scan point stores.
    **kwargs:
        Passed on to :func:`.normalize_scan`.

    Returns
    -------
    :
        Arrays over the N pixel contributions of all scan points:

        - ``q``: (N, 3) sample-frame Q in 1/Å;
        - ``w``: normalized weight in 1/sr;
        - ``var``: Monte Carlo variance of ``w``, the sum of squared event weights;
        - ``scan``: index of the scan point;

        and per scan point:

        - ``monitor``, ``monitor_err``: incident monitor intensity and its uncertainty.
    """
    scan = normalize_scan(folder, **kwargs)
    q, w, var, idx, mon, mon_err = [], [], [], [], [], []
    for k, group in enumerate(scan.values()):
        params = {key: v.value for key, v in group["parameters"].items()}
        events = group["events"]
        # sum of squared event weights per pixel = variance of the pixel's summed weight
        c = events.bins.constituents
        sq = sc.DataArray(c["data"].data * c["data"].data, coords=c["data"].coords)
        sq_per_pixel = sc.bins(begin=c["begin"], dim=c["dim"], data=sq).bins.sum()
        pixels = events.bins.sum()
        qs = to_sample_frame(to_Q(pixels, run_wavelength(params, wavelength)), params)
        q.append(np.stack([qs.coords[f"{a}_sample"].values for a in ("Qx", "Qy", "Qz")], axis=1))
        w.append(pixels.values)
        var.append(sq_per_pixel.values)
        idx.append(np.full(len(w[-1]), k))
        mon.append(group["monitor_intensity"].value)
        mon_err.append(np.sqrt(group["monitor_intensity"].variance))
    return {
        "q": np.concatenate(q),
        "w": np.concatenate(w),
        "var": np.concatenate(var),
        "scan": np.concatenate(idx),
        "monitor": np.array(mon),
        "monitor_err": np.array(mon_err),
    }


def centre_of_mass(
    q: np.ndarray,
    w: np.ndarray,
    var: np.ndarray,
    scan: np.ndarray,
    monitor: np.ndarray,
    monitor_err: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Compute the centre of mass of weighted points, with propagated uncertainties.

    The model is ``w_i = p_i / (I0_k Omega_i)``, with independent event sums ``p_i`` and one
    monitor reading ``I0_k`` per scan point ``k``.

    Parameters
    ----------
    q:
        (N, 3) point positions.
    w:
        (N,) weights.
    var:
        (N,) variances of ``w`` from the event statistics.
    scan:
        (N,) scan point index of each point.
    monitor, monitor_err:
        Monitor reading ``I0_k`` and its uncertainty, per scan point.

    Returns
    -------
    q_c:
        (3,) centre of mass.
    cov:
        (3, 3) covariance of ``q_c``.
    W:
        Total weight.
    W_err:
        Uncertainty of ``W``.
    """
    W = w.sum()
    qc = w @ q / W
    d = q - qc  # dQc/dw_i = d_i / W
    cov = (d * var[:, None]).T @ d / W**2  # statistics of the events

    var_W = var.sum()
    for k in np.unique(scan):
        m = scan == k
        # w_i ~ 1/I0_k, so dQc/dI0_k = -sum_i w_i d_i / (I0_k W) and dW/dI0_k = -W_k / I0_k
        g = -(w[m, None] * d[m]).sum(axis=0) / (monitor[k] * W)
        cov += monitor_err[k] ** 2 * np.outer(g, g)
        var_W += (monitor_err[k] * w[m].sum() / monitor[k]) ** 2
    return qc, cov, W, np.sqrt(var_W)


def find_peaks(
    folder: str | Path,
    wavelength: sc.Variable | None = None,
    voxel: float = 0.04,
    smooth: float = 1.0,
    nsigma: float = 20.0,
    radius: float = 0.1,
    min_points: int = 5,
    min_significance: float = 3.0,
    points: dict[str, np.ndarray] | None = None,
    monitor_file: str | Path | None = None,
) -> list[Peak]:
    """Find peaks in the sample-frame Q space of a scan.

    The points are histogrammed on a grid and smoothed. Local maxima that exceed the background
    (median of the occupied voxels) by ``nsigma`` robust standard deviations (MAD) are peak
    candidates. Every point in a voxel above that threshold belongs to the nearest candidate
    within ``radius``.

    Parameters
    ----------
    folder:
        Run folder with the ``mccode.h5`` of the scan.
    wavelength:
        Scalar wavelength, passed to :func:`load_points`. If ``None``, the one the scan stores.
    voxel:
        Grid spacing in 1/Å.
    smooth:
        Width of the Gaussian smoothing, in voxels.
    nsigma:
        Threshold above the background, in robust standard deviations.
    radius:
        Maximum distance of a point from its peak's maximum, in 1/Å. Keep it below half the
        lattice spacing so neighbouring peaks are not merged.
    min_points:
        Peaks with fewer pixel contributions are dropped.
    min_significance:
        Peaks with an intensity below this many times its uncertainty are dropped.
    points:
        Output of :func:`load_points`, to reuse loaded data. If ``None``, loaded from
        ``folder``.
    monitor_file:
        For data from ``scan_from_sample``, the beam run's ``mccode.h5``; see
        :func:`.normalize_scan`.

    Returns
    -------
    :
        The peaks, strongest first.
    """
    p = points if points is not None else load_points(folder, wavelength, monitor_file=monitor_file)
    q = p["q"]
    lo = q.min(axis=0) - 2 * voxel
    shape = np.ceil((q.max(axis=0) + 2 * voxel - lo) / voxel).astype(int)
    index = np.floor((q - lo) / voxel).astype(int)
    grid = np.zeros(shape)
    np.add.at(grid, tuple(index.T), p["w"])
    grid = ndimage.gaussian_filter(grid, smooth)

    occupied = grid[grid > 0]
    background = np.median(occupied)
    spread = 1.4826 * np.median(np.abs(occupied - background))
    threshold = background + nsigma * spread
    is_max = (grid == ndimage.maximum_filter(grid, size=3)) & (grid > threshold)
    maxima = lo + (np.argwhere(is_max) + 0.5) * voxel  # voxel centres
    if len(maxima) == 0:
        return []
    above = grid[tuple(index.T)] > threshold
    dist, nearest = cKDTree(maxima).query(q, distance_upper_bound=radius)
    member = above & np.isfinite(dist)

    peaks = []
    for label in range(len(maxima)):
        m = member & (nearest == label)
        if m.sum() < min_points:
            continue
        qc, cov, W, W_err = centre_of_mass(
            q[m], p["w"][m], p["var"][m], p["scan"][m], p["monitor"], p["monitor_err"]
        )
        if W < min_significance * W_err:
            continue
        peaks.append(Peak(qc, cov, W, W_err, int(m.sum())))
    return sorted(peaks, key=lambda pk: -pk.intensity)
