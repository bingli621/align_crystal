"""Normalization of the detector events by the incident monitor and the pixel solid angle."""

from pathlib import Path

import mcstastox
import numpy as np
import scipp as sc

from mcstas_to_sqe.mcstas.nexus_io import numeric_parameters

from .solid_angle import Geometry, rectangle_solid_angle


def detector_solid_angle(
    folder: str | Path,
    component: str = "detector",
    sample: str = "sample_pos",
    geometry: Geometry = "cylinder",
) -> sc.DataArray:
    """Compute the solid angle of every pixel of a banana (theta, y) detector.

    The pixel size comes from the detector's bin axes: ``radius * d(theta)`` wide (arc length)
    and ``d(y)`` high.

    Parameters
    ----------
    folder:
        Run folder with the ``mccode.h5``.
    component:
        Name of the detector component.
    sample:
        Name of the sample position component.
    geometry:
        Detector geometry; see :func:`.rectangle_solid_angle`.

    Returns
    -------
    :
        Solid angle in sr over ``pixel_id``, with the pixel ``position`` coord. Includes pixels
        that received no neutrons.
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


def incident_intensity(data: mcstastox.Read, monitor: str = "incident_monitor") -> sc.Variable:
    """Read the integrated intensity of the incident-beam monitor.

    The McStas ``Monitor`` stores ``I I_err N`` as one string in the ``values`` attribute of
    its output dataset.

    Parameters
    ----------
    data:
        An open ``mcstastox.Read``, which selects the scan entry.
    monitor:
        Name of the monitor component.

    Returns
    -------
    :
        Scalar intensity with its variance, in ``counts``.
    """
    output = data.file_object.get_output_entry(monitor)
    values = output[f"{monitor}_dat"].attrs["values"].decode().split()
    intensity, error = float(values[0]), float(values[1])
    return sc.scalar(intensity, variance=error**2, unit="counts")


def normalize_scan(
    folder: str | Path,
    out: str | Path | None = None,
    component: str = "detector",
    source: str = "source",
    sample: str = "sample_pos",
    monitor: str = "incident_monitor",
    monitor_file: str | Path | None = None,
) -> sc.DataGroup:
    """Normalize the events of every scan point, and optionally save them.

    Each event weight is divided by the incident monitor intensity and by the solid angle of the
    pixel it hit, giving intensity per incident neutron per steradian (1/sr). The events keep
    their pixel grouping (``pixel_id``, ``position``, ``t`` coords).

    Parameters
    ----------
    folder:
        Run folder with the ``mccode.h5`` of the scan.
    out:
        If given, the result is also saved there with scipp's HDF5 writer; read it back with
        ``scipp.io.load_hdf5``.
    component:
        Name of the detector component.
    source:
        Name of the source component.
    sample:
        Name of the sample position component.
    monitor:
        Name of the incident monitor component.
    monitor_file:
        ``mccode.h5`` of the beam run, for data simulated from a beam dump
        (``scan_from_sample``); see :func:`.monitor_file`. If ``None``, the monitor is read
        from every scan entry of ``folder``.

    Returns
    -------
    :
        One group per scan point (``entry1``, ``entry2``, ...) with the instrument
        ``parameters``, the ``monitor_intensity`` and the normalized ``events``.

    Notes
    -----
    In a split run the monitor and the source are only in the beam run's file
    (``mcstas_output/<time>_run_to_sample/mccode.h5``). With ``monitor_file``:

    - that one monitor reading normalizes all scan points;
    - the source position is rebuilt from the beam run's source -> sample vector, so the
      incident beam direction is known;
    - the beam run's parameters fill in those the scan entries lack, e.g. the energy, which a
      split run does not store since the source is not in it.
    """
    folder = Path(folder)
    solid_angle = detector_solid_angle(folder, component, sample)

    with mcstastox.Read(str(folder)) as data:
        n_entries = data.get_number_of_entries()

    beam_incident = beam_source_to_sample = None
    beam_params = {}
    if monitor_file is not None:
        monitor_file = Path(monitor_file)
        with mcstastox.Read(str(monitor_file.parent), filename=monitor_file.name) as beam:
            beam_incident = incident_intensity(beam, monitor)
            beam_params = numeric_parameters(beam.get_instrument_parameters())
            beam_source_to_sample = beam.get_global_component_coordinates(
                f"MCPL_{sample}"
            ) - beam.get_global_component_coordinates(source)

    result = sc.DataGroup()
    for entry in range(1, n_entries + 1):
        with mcstastox.Read(str(folder), entry_number=entry) as data:
            # the entry's own values win (omega, chi, phi); the beam run gives e.g. the energy
            params = beam_params | numeric_parameters(data.get_instrument_parameters())
            if monitor_file is None:
                events = data.export_scipp(source, sample, component_name=component)["events"]
                incident = incident_intensity(data, monitor)
            else:
                # the source is not in the file: use the sample as a stand-in and fix it below
                events = data.export_scipp(sample, sample, component_name=component)["events"]
                events.coords["source_position"] = sc.vector(
                    events.coords["sample_position"].value - beam_source_to_sample,
                    unit="m",
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
