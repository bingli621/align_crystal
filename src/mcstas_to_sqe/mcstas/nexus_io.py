"""Read and write McStas NeXus (HDF5) output.

- :func:`read_scan` reads a scan with mcstastox.
- :func:`merge_entries` merges single-run files into one scan file.

A scan file holds one entry per scan point (entry1, entry2, ...). Reading it needs the mcstastox
branch with ``entry_number`` support (https://github.com/mads-bertelsen-agentic/McStasToX,
branch entry_choice).
"""

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import h5py
import mcstastox
import numpy as np
import scipp as sc


def numeric_parameters(parameters: Mapping[str, Any]) -> dict[str, float]:
    """Keep the instrument parameters that are numbers.

    Parameters
    ----------
    parameters:
        Instrument parameters by name.

    Returns
    -------
    :
        The numeric ones as floats. Others, e.g. the beam file name, are dropped.
    """
    numeric = {}
    for key, value in parameters.items():
        try:
            numeric[key] = float(value)
        except (TypeError, ValueError):
            pass
    return numeric


def read_scan(
    folder: str | Path,
    component: str = "detector",
    source: str = "source",
    sample: str = "sample_pos",
) -> list[tuple[dict[str, float], sc.DataArray]]:
    """Read every scan point of a McStas NeXus file.

    Parameters
    ----------
    folder:
        Run folder with the ``mccode.h5`` to read.
    component:
        Name of the detector component.
    source:
        Name of the source component.
    sample:
        Name of the sample position component.

    Returns
    -------
    :
        One ``(parameters, pixels)`` per scan point:

        - ``parameters``: the numeric instrument parameters of the point.
        - ``pixels``: intensity summed per pixel, over ``pixel_id``. Only pixels that were hit
          are included. Coords are ``position``, ``pixel_id``, ``gamma`` and ``y``.
          ``gamma`` is the signed in-plane scattering angle in deg, negative to the right of the
          beam (not scippneutron's ``two_theta``, the full angle between ki and kf). ``y`` is the
          height above the sample in m.

    Notes
    -----
    A split run (``scan_from_sample``) has no source in its file. Its ``source_position`` is
    then put 1 m upstream of the sample along the beam (+z), which gives the right incident
    direction for the elastic Q; the distance does not matter.
    """
    points = []
    with mcstastox.Read(str(folder)) as data:
        n_entries = data.get_number_of_entries()

    for entry in range(1, n_entries + 1):
        with mcstastox.Read(str(folder), entry_number=entry) as data:
            params = numeric_parameters(data.get_instrument_parameters())
            sample_pos = data.get_global_component_coordinates(sample)
            try:
                grouped = data.export_scipp(source, sample, component_name=component)["events"]
            except ValueError:  # no source in the file: a split run
                grouped = data.export_scipp(sample, sample, component_name=component)["events"]
                grouped.coords["source_position"] = sc.vector(sample_pos - [0, 0, 1.0], unit="m")

        pixels = grouped.bins.sum()  # events are grouped by pixel id; sum the weights
        x, y, z = (pixels.coords["position"].values - sample_pos).T
        pixels.coords["gamma"] = sc.array(
            dims=["pixel_id"], values=np.degrees(np.arctan2(x, z)), unit="deg"
        )
        pixels.coords["y"] = sc.array(dims=["pixel_id"], values=y, unit="m")
        points.append((params, pixels))
    return points


def merge_entries(files: Iterable[str | Path], merged: Path) -> Path:
    """Merge single-entry McStas files into one scan file.

    Parameters
    ----------
    files:
        McStas NeXus files, each with one entry ``entry1``.
    merged:
        File to write, overwritten if it exists.

    Returns
    -------
    :
        ``merged``, with the entries ``entry1``, ``entry2``, ... in the order of ``files``.
    """
    with h5py.File(merged, "w") as out:
        for n, file in enumerate(files, start=1):
            with h5py.File(file) as part:
                part.copy(part["entry1"], out, name=f"entry{n}")
    return merged
