"""Peak list from the normalized events in the sample-frame Q space.

Every detector pixel hit in every scan point is one point in (Qx, Qy, Qz)_sample with a normalized
weight w = sum(p) / (I0 * solid_angle) [1/sr]. Peaks are connected regions of high density in this
point cloud; the peak position is the centre of mass of the weights in the region, and the
uncertainties are propagated from the Monte Carlo statistics of the events and from the
incident-monitor uncertainty of each scan point.
"""

from dataclasses import dataclass

import numpy as np
import scipp as sc
from scipy import ndimage
from scipy.spatial import cKDTree

from align_crystal.normalization import normalize_scan
from align_crystal.reduction import to_Q, to_sample_frame


@dataclass
class Peak:
    """A peak in the sample-frame Q space. Q in 1/angstrom; intensity in 1/sr, summed over the
    scan points (not divided by the scan step)."""

    q: np.ndarray  # centre of mass, (3,) Qx, Qy, Qz
    q_cov: np.ndarray  # covariance of q, (3, 3)
    intensity: float
    intensity_err: float
    n_points: int  # detector pixels (over all scan points) in the peak

    @property
    def q_err(self):
        return np.sqrt(np.diag(self.q_cov))


def load_points(folder, **kwargs):
    """Normalized scan as a point cloud in the sample-frame Q space.

    Returns a dict with arrays over the pixel contributions of all scan points: `q` (N, 3),
    `w` (normalized weight), `var` (its Monte Carlo variance, sum of squared event weights),
    `scan` (scan point index), and per scan point `monitor` and `monitor_err` (n/s).
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
        qs = to_sample_frame(to_Q(pixels, sc.scalar(params["wavelength"], unit="angstrom")), params)
        q.append(np.stack([qs.coords[f"{a}_sample"].values for a in ("Qx", "Qy", "Qz")], axis=1))
        w.append(pixels.values)
        var.append(sq_per_pixel.values)
        idx.append(np.full(len(w[-1]), k))
        mon.append(group["monitor_intensity"].value)
        mon_err.append(np.sqrt(group["monitor_intensity"].variance))
    return dict(
        q=np.concatenate(q),
        w=np.concatenate(w),
        var=np.concatenate(var),
        scan=np.concatenate(idx),
        monitor=np.array(mon),
        monitor_err=np.array(mon_err),
    )


def centre_of_mass(q, w, var, scan, monitor, monitor_err):
    """Centre of mass of the weights `w` at the points `q` (N, 3) with propagated errors.

    Model: w_i = p_i / (I0_k Omega_i), with independent p_i (variance `var`) and one monitor
    reading I0_k +- monitor_err per scan point k (`scan`). Returns q_c, its (3, 3) covariance,
    the total weight and its uncertainty.
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
    folder,
    voxel=0.04,
    smooth=1.0,
    nsigma=20.0,
    radius=0.1,
    min_points=5,
    min_significance=3.0,
    points=None,
):
    """Find peaks in the sample-frame Q space of a scan; strongest first.

    The points are histogrammed on a grid with `voxel` (1/angstrom) spacing and smoothed with a
    Gaussian of `smooth` voxels. Local maxima that exceed the background (median of the occupied
    voxels) by `nsigma` robust standard deviations (MAD) are peak candidates. Every point in a
    voxel above that threshold belongs to the nearest candidate if it is within `radius`
    (1/angstrom, keep it below half the lattice spacing so neighbours are not merged). Peaks with
    fewer than `min_points` pixel contributions, or an intensity below `min_significance` times
    its uncertainty, are dropped. Pass `points` (from `load_points`)
    to reuse already loaded data.
    """
    p = points if points is not None else load_points(folder)
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
