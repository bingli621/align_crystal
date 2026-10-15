# align_crystal

[![CI](https://github.com/bingli621/align_crystal/actions/workflows/ci.yml/badge.svg)](https://github.com/bingli621/align_crystal/actions/workflows/ci.yml)

Single-crystal diffractometer simulation (McStasScript) with a three-axis goniometer, and
tools to read the McStas NeXus output (McStasToX, scippneutron) and convert to momentum transfer.

## Layout

```
src/align_crystal/   the library (installed)
  instrument/       the entities: the diffractometer is a set of components (no McStas knowledge)
    components/       the components, one dataclass each, named after the McStas component
                      (misc.py: Component, Progress_bar, Slit, Arm; source.py: Source_simple;
                       detector.py: Monitor, Monitor_nD; sample.py: Single_crystal, aluminum, la2ni7)
    params.py         DesignParam: the design parameters, as one nested dict (`from_dict`); InstrParams
    cif/              a plain folder: La2Ni7.cif (ready-made crystals: aluminum(), la2ni7() in components/sample.py)
    model/            this instrument, the single-crystal diffractometer
      diffractometer.py SingleCrystalDiffractometer: its components, each recording where it sits, and its
                        rule for the source focus (its distance follows from the component it focuses on)
      builder.py        build_diffractometer(crystal=None): the default diffractometer made in code, with
                        the given crystal as its sample (None: no sample)
      params.yaml       the complete default parameters; it names the components in beam order
  yaml_io.py    the only module that knows YAML: yaml_loader (the default loader), write_yaml
  mcstas/       everything that talks to McStas
    builder.py        builds the McStasScript instrument from the diffractometer (goniometer: omega Y, chi -Z, phi X)
    simulater.py      run, dump_beam, run_from_beam (also runnable as a script); `config` is the diffractometer
    h5_reader.py      read_scan: the NeXus output via mcstastox
  reduction/    to_Q, to_sample_frame, solid-angle normalization, find_peaks
scripts/        plot_scan_2d.py, plot_scan_Q.py (gifs), print_peaks.py
tests/
mcstas_output/  generated McStas files and simulation results (git-ignored)
```

Dependencies point inwards: `instrument` takes and gives plain nested dicts (`from_dict`, `to_dict`) and imports
nothing from the outer layers; only `build_diffractometer(file=...)` loads `yaml_io`, when no other loader (any function from a
path to a dict) is given. `mcstas` simulates a `SingleCrystalDiffractometer` that the caller creates;
the sample is the diffractometer's `crystal` (a `Single_crystal`, optional); `reduction` reads the McStas output with `mcstas.h5_reader`.

## Configuration

The diffractometer is built in code, by `build_diffractometer()` (`instrument/model/builder.py`): the
components in the order of the beam, with their values. Its components are plain attributes
(`d.slit.xwidth = 0.02`); what follows from them (the source's focus distance, the crystal's
reciprocal vectors) is computed when used, and `d.validate()` checks the whole again (the McStas builder does).

A parameters file is laid over the built one, so it need hold only what differs: a value it gives
wins, one it leaves out, or sets to `null`, stays as built. Its layout is that of
`src/align_crystal/instrument/model/params.yaml`, the built diffractometer saved (a test keeps them equal): `instr_params` (the instrument parameter
parameters, see below) and one section per component name: its `component` (the McStas component),
its parameters, and last where it sits (`at`, `rotated`, `relative`). Save your own with
`write_yaml(d.to_dict(), "copy.yaml")`, edit it, and load it with `build_diffractometer(file="copy.yaml")`.
Unknown keys, and values missing from both, are errors.

The parameters are one nested dict (`DesignParam`). A value left `null` is computed when used, not
saved: the source's focus distance `dist` is the position of the component it focuses on (`focus_on`).
Components never see the file.

The instrument parameters (`InstrParams`) are the McStas instrument parameters, which each run may
set. The components are general: the file declares them in its `instr_params` section (start
`value`, `unit`, `comment`; a null value must be given by every run), and where a component takes a
number it names an instrument parameter instead (or an expression of them), as in McStas: the diffractometer's
goniometer arms have `rotated: [0, omega, 0]` etc. A name that is not an instrument parameter is an error.
`diffractometer.instrument_param(omega=30)` gives them all, with the values a run sets in place of the
start values; `.complete()` raises on one still unset.

The control parameters (`ControlParam`) are given when the instrument is made, for now the incident
energy `ei` (meV): `build_diffractometer(crystal, ControlParam(ei=14))`; it is kept in the source (`source.ei`). The source converts
it to a wavelength (`source.wavelength`), which is the instrument parameter `wavelength` McStas gets
(`lambda0`), unless a run sets it. The reduction takes
the wavelength from the caller: `find_peaks(folder, wavelength(14))`.

```yaml
# my_params.yaml: only what differs from the built diffractometer, for example
source:
  radius: 0.02
detector:
  n_theta: 600
slit:
  at: [0, 0, 1.2]
```

```python
from align_crystal.mcstas.simulater import run
from align_crystal.instrument import ControlParam, build_diffractometer

# config: the diffractometer to simulate, the built one with the file laid over it
h5 = run(
    config=build_diffractometer(control=ControlParam(ei=14), file="my_params.yaml"),
    omega="-48,73",
    custom_flags="-N 122",
)  # scan omega

# a sample: the crystal of the diffractometer (none by default)
from align_crystal.instrument import ControlParam, la2ni7

h5 = run(
    config=build_diffractometer(
        la2ni7(mosaic=60, at=[0, 0, 0], relative="gonio_phi"), ControlParam(ei=14)
    ),
    omega="-48,73",
    custom_flags="-N 122",
)
```

A diffractometer can be created in these ways:

```python
from align_crystal.instrument import SingleCrystalDiffractometer, build_diffractometer
from align_crystal.yaml_io import yaml_loader, write_yaml

# the built one, in code (instrument/model/builder.py)
d = build_diffractometer()
# with a file laid over it (read with a loader: YAML by default)
d = build_diffractometer(file="my_params.yaml")
d = build_diffractometer(file="my_params.yaml", loader=yaml_loader)
# from a complete dict
d = SingleCrystalDiffractometer.from_dict(d.to_dict())
# change it, and check it again
d.slit.xwidth = 0.02
d.validate()
# save its parameters
write_yaml(d.to_dict(), "copy.yaml")
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
