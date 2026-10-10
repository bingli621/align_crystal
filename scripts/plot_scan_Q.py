"""Animated (Qx, Qz) maps over a McStas scan: intensity summed over Qy, one frame per scan point.

Q is the elastic momentum transfer (scippneutron) rotated into the sample frame with the inverse
goniometer rotation, so the reciprocal lattice stays fixed while omega changes.

In VS Code: run this file, or from a notebook/Interactive Window:

    from plot_scan_Q import plot_scan_Q
    plot_scan_Q("mcstas_output/latest", scan_par="omega", out="output/scan_Q.gif")
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import scipp as sc
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import LogNorm

from align_crystal.mcstas.h5_reader import read_scan
from align_crystal.reduction import normalize_scan, to_Q, to_sample_frame

ROOT = Path(__file__).resolve().parents[1]


def plot_scan_Q(
    folder=ROOT / "mcstas_output" / "latest",
    scan_par="omega",
    out=ROOT / "output" / "scan_Q.gif",
    bins=(200, 200),
    fps=3,
    accumulate=True,
    normalize=False,
    monitor_file=None,
    show=True,
):
    """Saves a gif to `out` (None: don't save); returns the FuncAnimation.

    With `normalize`, the intensities are divided by the incident monitor and the pixel solid
    angle (see `normalize_scan`), in 1/sr. For data from `run_from_beam` give the beam run's
    `monitor_file` (`mcstas_output/beam/mccode.h5`).

    With `accumulate`, frame i shows the sum of all scan points up to i (previous frames are kept).
    """
    if normalize:
        scan = normalize_scan(folder, monitor_file=monitor_file)
        points = [
            ({k: v.value for k, v in g["parameters"].items()}, g["events"].bins.sum())
            for g in scan.values()
        ]
    else:
        points = read_scan(folder)
    qs = [
        to_sample_frame(to_Q(ev, sc.scalar(p["wavelength"], unit="angstrom")), p)
        for p, ev in points
    ]

    # common Qx/Qz range so frames are comparable
    qx_all = np.concatenate([q.coords["Qx_sample"].values for q in qs])
    qz_all = np.concatenate([q.coords["Qz_sample"].values for q in qs])
    rng = [[qx_all.min(), qx_all.max()], [qz_all.min(), qz_all.max()]]
    # histogramming over (Qx, Qz) with weights sums the intensity over Qy
    hists = [
        np.histogram2d(q.coords["Qx_sample"].values, q.coords["Qz_sample"].values, bins=bins, range=rng, weights=q.values)[0]
        for q in qs
    ]
    if accumulate:
        hists = list(np.cumsum(hists, axis=0))
    xe = np.linspace(*rng[0], bins[0] + 1)
    ye = np.linspace(*rng[1], bins[1] + 1)

    vmax = max(h.max() for h in hists)
    vmin = max(min(h[h > 0].min() for h in hists), vmax * 1e-6)

    fig, ax = plt.subplots(figsize=(7, 6))
    mesh = ax.pcolormesh(
        xe, ye, np.ma.masked_less_equal(hists[0].T, 0), cmap="jet", norm=LogNorm(vmin, vmax)
    )
    fig.colorbar(mesh, label="normalized intensity summed over Qy (1/sr)" if normalize else "intensity summed over Qy (n/s)")
    ax.set_xlabel("Qx sample (1/Å)")
    ax.set_ylabel("Qz sample (1/Å)")
    ax.set_aspect("equal")
    ax.grid(alpha=0.6)
    ax.set_title(f"{scan_par} = {points[0][0][scan_par]:g}°")  # reserve room before tight_layout
    fig.tight_layout()

    def draw(i):
        mesh.set_array(np.ma.masked_less_equal(hists[i].T, 0))
        ax.set_title(f"{scan_par} = {points[i][0][scan_par]:g}°")
        return (mesh,)

    anim = FuncAnimation(fig, draw, frames=len(points), blit=False)
    draw(0)
    if out is not None:
        Path(out).parent.mkdir(exist_ok=True)
        anim.save(out, writer=PillowWriter(fps=fps))
    if show:
        plt.show()
    return anim


if __name__ == "__main__":
    # normalized (Qx, Qz) map of a run_from_beam scan, using the monitor of the beam run
    plot_scan_Q(
        folder=ROOT / "mcstas_output" / "split",
        out=ROOT / "output" / "scan_Q_normalized.gif",
        normalize=True,
        monitor_file=ROOT / "mcstas_output" / "beam" / "mccode.h5",
    )
