# align_crystal

[![CI](https://github.com/bingli621/align_crystal/actions/workflows/ci.yml/badge.svg)](https://github.com/bingli621/align_crystal/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/bingli621/align_crystal/branch/main/graph/badge.svg)](https://codecov.io/gh/bingli621/align_crystal)

Single-crystal diffractometer simulation (McStasScript) with a three-axis goniometer, and
tools to read the McStas NeXus output (McStasToX, scippneutron) and convert to momentum transfer.

## Layout

- `src/align_crystal/instrument.py` – the McStasScript instrument; goniometer: omega (Y), chi (-Z), phi (X).
- `src/align_crystal/samples.py` – crystals and their orientation (`la2ni7()`, `aluminium()`).
- `src/align_crystal/simulate.py` – `run(...)`, also runnable as a script; supports mcrun scans
  (`omega="-48,73"`, `custom_flags="-N 122"`). McStas-generated files go to `work/`.
- `src/align_crystal/io.py` – `read_scan` (mcstastox), `to_Q` (lab-frame Q), `to_sample_frame`.
- `scripts/plot_scan_2d.py`, `scripts/plot_scan_Q.py` – gifs of the detector and of (Qx, Qz) in the sample frame.

## Use

```bash
pixi run python src/align_crystal/simulate.py        # writes work/latest/mccode.h5
pixi run python scripts/plot_scan_2d.py      # output/scan.gif
pixi run python scripts/plot_scan_Q.py       # output/scan_Q.gif
pixi run pytest --cov=align_crystal --cov-report=term-missing   # tests + coverage
```

`mcstastox` is installed from the `entry_choice` branch, which can read individual scan entries.
