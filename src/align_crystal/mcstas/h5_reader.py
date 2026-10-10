"""Read McStas NeXus (HDF5) output, including mcrun scans, with mcstastox.

A scan file holds one entry per scan point (entry1, entry2, ...). This needs the mcstastox
branch with `entry_number` support (https://github.com/mads-bertelsen-agentic/McStasToX,
branch entry_choice).
"""

import mcstastox
import numpy as np
import scipp as sc


def numeric_parameters(parameters):
    """The instrument parameters that are numbers, as floats (drops e.g. the beam file name)."""
    numeric = {}
    for key, value in parameters.items():
        try:
            numeric[key] = float(value)
        except (TypeError, ValueError):
            pass
    return numeric


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
            params = numeric_parameters(data.get_instrument_parameters())
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
