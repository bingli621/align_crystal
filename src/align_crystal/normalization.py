"""Normalization of the detector events: incident monitor intensity and pixel solid angle."""

from pathlib import Path

import mcstastox
import numpy as np
import scipp as sc

from align_crystal.io import numeric_parameters
from align_crystal.solid_angle import rectangle_solid_angle


def detector_solid_angle(folder, component="detector", sample="sample_pos", geometry="cylinder"):
    """Solid angle [sr] of every pixel of a banana (theta, y) detector, as a scipp DataArray over
    'pixel_id' with the pixel `position` coordinate. Includes pixels that received no neutrons.

    The pixel size comes from the detector's bin axes: arc length radius * d(theta) wide and
    d(y) high.
    """
    with mcstastox.Read(str(folder)) as data:
        theta = data.file_object.get_x_var_and_axis(component)[1]
        y = data.file_object.get_y_var_and_axis(component)[1]
        radius = data.file_object.get_geometry_dict(component)["radius"]
        positions = data.get_id_to_global_coordinates(component_name=component)
        sample_pos = data.get_global_component_coordinates(sample)
    width = radius * np.radians(np.diff(theta).mean())
    height = np.diff(y).mean()
    rel = positions - sample_pos
    omega = rectangle_solid_angle(rel, width, height, geometry)
    return sc.DataArray(
        sc.array(dims=["pixel_id"], values=omega, unit="sr"),
        coords={"position": sc.vectors(dims=["pixel_id"], values=positions, unit="m")},
    )


def incident_intensity(data, monitor="incident_monitor"):
    """Integrated intensity [n/s] of the incident-beam monitor, as a scipp scalar with variance.

    `data` is an open `mcstastox.Read` (it selects the scan entry). The McStas `Monitor` stores
    `I  I_err  N` as one string in the `values` attribute of its output dataset.
    """
    output = data.file_object.get_output_entry(monitor)
    values = output[f"{monitor}_dat"].attrs["values"].decode().split()
    intensity, error = float(values[0]), float(values[1])
    return sc.scalar(intensity, variance=error**2, unit="counts")


def normalize_scan(
    folder,
    out=None,
    component="detector",
    source="source",
    sample="sample_pos",
    monitor="incident_monitor",
    monitor_file=None,
):
    """Normalize all events of every scan point; optionally save them.

    Each event weight is divided by the incident monitor intensity and by the solid angle of the
    pixel it hit, giving intensity per incident neutron per steradian [1/sr]. The events keep
    their pixel grouping (`pixel_id`, `position`, `t` coordinates).

    The monitor is read from every scan entry of `folder`, unless `monitor_file` is given: for
    data simulated from a beam dump (`run_from_beam`) the monitor and the source are only in the
    file of the beam run (`dump_beam`, `work/beam/mccode.h5`). That one monitor reading then
    normalizes all angles, and the source position is rebuilt from the beam file (source ->
    sample vector) so that the incident beam direction is known.

    Returns a scipp DataGroup with one group per scan point (`entry1`, `entry2`, ...) holding
    the instrument `parameters`, the `monitor_intensity` and the normalized `events`. If `out` is
    given it is also saved there with scipp's HDF5 writer (`scipp.io.load_hdf5` reads it back).
    """
    folder = Path(folder)
    solid_angle = detector_solid_angle(folder, component, sample)

    with mcstastox.Read(str(folder)) as data:
        n_entries = data.get_number_of_entries()

    beam_incident = beam_source_to_sample = None
    if monitor_file is not None:
        monitor_file = Path(monitor_file)
        with mcstastox.Read(str(monitor_file.parent), filename=monitor_file.name) as beam:
            beam_incident = incident_intensity(beam, monitor)
            beam_source_to_sample = beam.get_global_component_coordinates(
                f"MCPL_{sample}"
            ) - beam.get_global_component_coordinates(source)

    result = sc.DataGroup()
    for entry in range(1, n_entries + 1):
        with mcstastox.Read(str(folder), entry_number=entry) as data:
            params = numeric_parameters(data.get_instrument_parameters())
            if monitor_file is None:
                events = data.export_scipp(source, sample, component_name=component)["events"]
                incident = incident_intensity(data, monitor)
            else:
                # the source is not in the file: use the sample as a stand-in and fix it below
                events = data.export_scipp(sample, sample, component_name=component)["events"]
                events.coords["source_position"] = sc.vector(
                    events.coords["sample_position"].value - beam_source_to_sample, unit="m"
                )
                incident = beam_incident

        # solid angle of each pixel that was hit (events are grouped by pixel_id)
        omega = sc.array(
            dims=["pixel_id"],
            values=solid_angle.values[events.coords["pixel_id"].values],
            unit="sr",
        )
        # drop the monitor's uncertainty: the events carry no variances to propagate it into
        normalized = events / (sc.scalar(incident.value, unit=incident.unit) * omega)
        result[f"entry{entry}"] = sc.DataGroup(
            parameters=sc.DataGroup({k: sc.scalar(v) for k, v in params.items()}),
            monitor_intensity=incident,
            events=normalized,
        )

    if out is not None:
        result.save_hdf5(str(out))
    return result
