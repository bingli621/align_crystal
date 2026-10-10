# align_crystal

[![CI](https://github.com/bingli621/align_crystal/actions/workflows/ci.yml/badge.svg)](https://github.com/bingli621/align_crystal/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/bingli621/align_crystal/branch/main/graph/badge.svg)](https://codecov.io/gh/bingli621/align_crystal)

Single-crystal diffractometer simulation (McStasScript) with a three-axis goniometer, and
tools to read the McStas NeXus output (McStasToX, scippneutron) and convert to momentum transfer.

## Layout

- `src/align_crystal/instrument/` – the instrument as dataclasses, one per component (`instrument.py`, no McStas knowledge), `config_yaml.py` to load/save a config, and `params.yaml` with all defaults (your file lists only the changes).
- `src/align_crystal/mcstas/` – everything that talks to McStas: `builder.py` (the McStasScript adapter: builds the instrument from a config; goniometer: omega (Y), chi (-Z), phi (X); `OUTPUT_DIR`), `simulater.py` (`run(...)`, also runnable as a script; supports mcrun scans
  (`omega="-48,73"`, `custom_flags="-N 122"`). McStas-generated files go to `mcstas_output/`) and `h5_reader.py` (`read_scan` of the NeXus output, mcstastox).
- `src/align_crystal/samples/` – `sample.py` (`Sample`, `oriented_sample`) and one folder per sample (`aluminium/`, `la2ni7/` with its CIF); `la2ni7()`, `aluminium()` are importable from `align_crystal.samples`.
- `src/align_crystal/reduction/` – `reduction.py` (`to_Q` lab-frame Q, `to_sample_frame`), `normalization.py` (`detector_solid_angle`, `normalize_scan`), `solid_angle.py` (the solid-angle math) and `peaks.py` (`find_peaks`: peak list in the sample-frame Q space, centre of mass, propagated errors); all re-exported from `align_crystal.reduction`.
- `scripts/plot_scan_2d.py`, `scripts/plot_scan_Q.py` – gifs of the detector and of (Qx, Qz) in the sample frame.

## Use

```bash
pixi run python src/align_crystal/mcstas/simulater.py # writes mcstas_output/latest/mccode.h5
pixi run python scripts/plot_scan_2d.py      # output/scan.gif
pixi run python scripts/plot_scan_Q.py       # output/scan_Q.gif
pixi run pytest --cov=align_crystal --cov-report=term-missing   # tests + coverage
```

`mcstastox` is installed from the `entry_choice` branch, which can read individual scan entries.
