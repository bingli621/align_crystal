"""Print the peak list (sample-frame Q, |Q|, intensity and its error bar) of a McStas scan, and
save it to a text file.

In VS Code: run this file, or from a notebook/Interactive Window:

    from print_peaks import print_peaks, save_peaks
    peaks = print_peaks("mcstas_output/latest")
    save_peaks(peaks, "output/peaks.txt")
"""

import sys
from pathlib import Path

import numpy as np

from align_crystal.reduction import find_peaks

ROOT = Path(__file__).resolve().parents[1]


def format_peaks(peaks):
    """The peak table as a list of text lines: Qx, Qy, Qz, |Q| [1/Å], Intensity, Errorbar [1/sr]."""
    lines = [f"{'Qx':>9} {'Qy':>9} {'Qz':>9} {'|Q|':>9} {'Intensity':>12} {'Errorbar':>10}"]
    for p in peaks:
        qx, qy, qz = p.q
        q_abs = np.linalg.norm(p.q)
        lines.append(
            f"{qx:9.4f} {qy:9.4f} {qz:9.4f} {q_abs:9.4f} {p.intensity:12.4g} {p.intensity_err:10.2g}"
        )
    lines.append(f"{len(peaks)} peaks")
    return lines


def save_peaks(peaks, out=ROOT / "output" / "peaks.txt"):
    """Write the peak table to the text file `out`; returns the path."""
    out = Path(out)
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(format_peaks(peaks)) + "\n")
    return out


def print_peaks(folder=ROOT / "mcstas_output" / "latest", **kwargs):
    """Print the peaks of a scan, smallest |Q| first. `kwargs` go to `find_peaks`.
    Returns the list of peaks (use `save_peaks` to write them to a file)."""
    peaks = sorted(find_peaks(folder, **kwargs), key=lambda p: np.linalg.norm(p.q))
    print("\n".join(format_peaks(peaks)))
    return peaks


if __name__ == "__main__":
    # optional command-line use: print_peaks.py [folder] [out.txt]
    peaks = print_peaks(*sys.argv[1:2])
    print(f"Saved to {save_peaks(peaks, *sys.argv[2:3])}")
