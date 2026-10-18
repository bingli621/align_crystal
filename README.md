# align_crystal

[![CI](https://github.com/bingli621/align_crystal/actions/workflows/ci.yml/badge.svg)](https://github.com/bingli621/align_crystal/actions/workflows/ci.yml)

Single-crystal diffractometer simulation (McStasScript) with a three-axis goniometer, and
tools to read the McStas NeXus output (McStasToX, scippneutron) and convert to momentum transfer.

## Layout

```
src/align_crystal/   the library (installed)
  instrument/       the entities: the diffractometer is a set of components (no files, no McStas)
    components/       the components, one dataclass each, named after the McStas component
                      (misc.py: Component, Progress_bar, Slit, Arm; source.py: Source_simple;
                       detector.py: Monitor, Monitor_nD; crystal.py: Single_crystal)
    samples/          the ready-made samples aluminum, la2ni7 (in __init__.py, which says how to add
                      one), with their CIF files (La2Ni7.cif)
    params.py         InstrParam: one instrument parameter
    geometry.py       rotation, place: the components' positions in the lab frame, as McStas places them
    utils.py          evaluate: a McStas expression of instrument parameters ("-chi"), safely;
                      format_value: a value short, for display
    diffractometer.py this instrument, SingleCrystalDiffractometer(sample, ei, omega, chi, phi):
                      makes its own components around the sample, each recording where it sits;
                      positions() gives where they are in the lab frame
  io/           files of the instrument (an adapter around the entities)
    dict_io.py        to_dict, from_dict: the diffractometer to and from its nested dict; over_default
    yaml_io.py        the only module that knows YAML: yaml_loader, write_yaml, load(file, sample, params)
    params.yaml       the default diffractometer saved; it names the components in beam order
  mcstas/       everything that talks to McStas
    builder.py        builds the McStasScript instrument from the diffractometer (goniometer: omega Y, chi -Z, phi X)
    simulater.py      run, dump_beam, run_from_beam (also runnable as a script); `config` is the diffractometer
    h5_reader.py      read_scan: the NeXus output via mcstastox
  reduction/    to_Q, to_sample_frame, solid-angle normalization, find_peaks
scripts/        plot_scan_2d.py, plot_scan_Q.py (gifs), print_peaks.py
tests/
mcstas_output/  generated McStas files and simulation results (git-ignored)
```

Dependencies point inwards (clean architecture): `instrument` holds the entities and imports nothing
from the outer layers (a test checks it). Around it are adapters: `io` converts the diffractometer
to and from its nested dict and YAML files, `mcstas` simulates a `SingleCrystalDiffractometer` that the caller creates;
the sample is the diffractometer's `sample` (a `Single_crystal`, optional); `reduction` reads the McStas output with `mcstas.h5_reader`.

## Configuration

The diffractometer makes itself in code, `SingleCrystalDiffractometer()` (`instrument/diffractometer.py`): the
components in the order of the beam, with their values. Its components are plain attributes
(`d.slit.xwidth = 0.02`); what follows from them (their positions in the lab frame, the sample's
reciprocal vectors) is computed when used. `print(d)` shows a summary (the params, the instrument
parameters, and a table of the components: where each sits and its position); `print(d.source)` shows
one component's values.

A parameters file is laid over the default one with `load(file, sample, params)`
(`io/yaml_io.py`), so it need hold only what differs: a value it gives wins, one it
leaves out, or sets to `null`, stays as made. Its layout is that of
`src/align_crystal/io/params.yaml`, the default diffractometer saved (a test keeps them equal): `params` (see below) and one
section per component name: its `component` (the McStas component),
its parameters, where it sits (`at`, `rotated`, `relative`), and last its `position` in the lab
frame (m; calculated with the diffractometer's angles, written for reading and never read back:
`d.positions()` gives them). Save your own with
`write_yaml(to_dict(d), "copy.yaml")`, edit it, and load it with `load("copy.yaml")`.

The parameters are one nested dict (`io/dict_io.py`). The source aims at the component it focuses on
(`focus_on`): the McStas builder sets its focus distance to that one's. Components never see the
file.

The sample (a `Single_crystal`, or None) and the params, the incident energy `ei` (meV) and the
goniometer angles `omega`, `chi`, `phi` (deg), are given when the instrument is made,
`SingleCrystalDiffractometer(sample, Params(ei=14, omega=0))`; by default 14 meV and all angles 0.
`Params` is a frozen dataclass: `d.params.ei` reads one, `d.params.ei = 25` raises, and
`d.update_params(ei=25)` changes them (an unknown name raises). The file holds them in its `params`
section.

The instrument parameters (`d.instr_params`, a list of `InstrParam`) are what McStas gets, calculated
from the params when used (never saved): the wavelength of `ei` (`Source_simple.wavelength_from_ei`; the source's
`lambda0` names it), and the goniometer angles. Where a component takes a number it names an
instrument parameter instead (or an expression of them), as in McStas: the goniometer arms have
`rotated: [0, omega, 0]` etc. A run may give its own values in place of the diffractometer's
(`run(config=d, omega=30)`).

Every McStas run records its wavelength and angles, and the
reduction reads them from the scan (`find_peaks(folder)`); give `find_peaks(folder, wavelength(14))`
for older scans that do not store it.

```yaml
# my_params.yaml: only what differs from the default diffractometer, for example
source:
  radius: 0.02
detector:
  n_theta: 600
slit:
  at: [0, 0, 1.2]
```

```python
from align_crystal.mcstas.simulater import run
from align_crystal.instrument import Params, SingleCrystalDiffractometer
from align_crystal.io import load

# config: the diffractometer to simulate, the default one with the file laid over it
h5 = run(
    config=load("my_params.yaml", params=Params(ei=14)),
    omega="-48,73",
    chi=0,
    phi=0,
    custom_flags="-N 122",
)  # scan omega

# a sample (none by default)
from align_crystal.instrument import la2ni7

h5 = run(
    config=SingleCrystalDiffractometer(
        la2ni7(mosaic=60, at=[0, 0, 0], relative="gonio_phi"), Params(ei=14)
    ),
    omega="-48,73",
    chi=-5.893,
    phi=0,
    custom_flags="-N 122",
)
```

A diffractometer can be created in these ways:

```python
from align_crystal.instrument import Params, SingleCrystalDiffractometer, la2ni7
from align_crystal.io import from_dict, load, to_dict, write_yaml, yaml_loader

# the default one, made in code (instrument/diffractometer.py)
d = SingleCrystalDiffractometer()
d = SingleCrystalDiffractometer(la2ni7(at=[0, 0, 0], relative="gonio_phi"), Params(ei=14))
# with a file laid over it (read with a loader: YAML by default)
d = load("my_params.yaml")
d = load("my_params.yaml", params=Params(ei=14), loader=yaml_loader)
# from a complete dict
d = from_dict(to_dict(d))
# change it
d.slit.xwidth = 0.02
# save its parameters
write_yaml(to_dict(d), "copy.yaml")
```

## Use

```bash
pixi run python src/align_crystal/mcstas/simulater.py   # edit MODE: one run, or beam dump + run from the beam
pixi run python scripts/plot_scan_2d.py                 # output/scan.gif
pixi run python scripts/plot_scan_Q.py                  # output/scan_Q.gif
pixi run python scripts/print_peaks.py                  # peak list of mcstas_output/latest
pixi run pytest --cov=align_crystal --cov-report=term-missing   # tests + coverage
pixi run pre-commit install                             # once: ruff format on every commit
```

Results go to `mcstas_output/` (`latest/`, and `beam/` + `split/` for the split run). A split run
simulates source to sample once (`dump_beam`) and then the crystal for many angles in parallel
(`run_from_beam`), which can be normalized with the beam run's incident monitor.

`mcstastox` is installed from the `entry_choice` branch, which can read individual scan entries.
