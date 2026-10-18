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
                       detector.py: Monitor, Monitor_nD; sample.py: Single_crystal, aluminum, la2ni7)
    params.py         InstrParam: one instrument parameter; with_values
    cif/              a plain folder: La2Ni7.cif (ready-made crystals: aluminum(), la2ni7() in components/sample.py)
    model/            this instrument, the single-crystal diffractometer
      diffractometer.py SingleCrystalDiffractometer(sample, ei, omega, chi, phi): makes its own
                        components around the sample, each recording where it sits;
                        the source focus distance follows from the component it focuses on
  io/           files of the instrument (an adapter around the entities)
    dict_io.py        to_dict, from_dict: the diffractometer to and from its nested dict; over_default
    yaml_io.py        the only module that knows YAML: yaml_loader, write_yaml, load(file, sample, **params)
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

The diffractometer makes itself in code, `SingleCrystalDiffractometer()` (`instrument/model/diffractometer.py`): the
components in the order of the beam, with their values. Its components are plain attributes
(`d.slit.xwidth = 0.02`); what follows from them (the source's focus distance, the sample's
reciprocal vectors) is computed when used.

A parameters file is laid over the default one with `load(file, sample, **params)`
(`io/yaml_io.py`), so it need hold only what differs: a value it gives wins, one it
leaves out, or sets to `null`, stays as made. Its layout is that of
`src/align_crystal/io/params.yaml`, the default diffractometer saved (a test keeps them equal): `params` (see below) and one
section per component name: its `component` (the McStas component),
its parameters, and last where it sits (`at`, `rotated`, `relative`). Save your own with
`write_yaml(to_dict(d), "copy.yaml")`, edit it, and load it with `load("copy.yaml")`.

The parameters are one nested dict (`io/dict_io.py`). A value left `null` is computed when used, not
saved: the source's focus distance `dist` is the position of the component it focuses on (`focus_on`).
Components never see the file.

The sample (a `Single_crystal`, or None) and the params, the incident energy `ei` (meV) and the
goniometer angles `omega`, `chi`, `phi` (deg), are given when the instrument is made,
`SingleCrystalDiffractometer(sample, ei=14, omega=0)`; by default 14 meV and all angles 0. The params
are kept in one place: `d.params` reads them (read-only), `d.update_params(ei=25)` changes them, and
the file holds them in its `params` section.

The instrument parameters (`d.instr_params`, a list of `InstrParam`) are what McStas gets, calculated
from the params when used (never saved): the wavelength of `ei` (`d.wavelength`; the source's
`lambda0` names it), and the goniometer angles. Where a component takes a number it names an
instrument parameter instead (or an expression of them), as in McStas: the goniometer arms have
`rotated: [0, omega, 0]` etc. `d.instrument_param(omega=30)` gives them all, with the values a run
gives in place of the diffractometer's.

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
from align_crystal.instrument import SingleCrystalDiffractometer
from align_crystal.io import load

# config: the diffractometer to simulate, the default one with the file laid over it
h5 = run(
    config=load("my_params.yaml", ei=14),
    omega="-48,73",
    chi=0,
    phi=0,
    custom_flags="-N 122",
)  # scan omega

# a sample (none by default)
from align_crystal.instrument import la2ni7

h5 = run(
    config=SingleCrystalDiffractometer(
        la2ni7(mosaic=60, at=[0, 0, 0], relative="gonio_phi"), ei=14
    ),
    omega="-48,73",
    chi=-5.893,
    phi=0,
    custom_flags="-N 122",
)
```

A diffractometer can be created in these ways:

```python
from align_crystal.instrument import SingleCrystalDiffractometer, la2ni7
from align_crystal.io import from_dict, load, to_dict, write_yaml, yaml_loader

# the default one, made in code (instrument/model/diffractometer.py)
d = SingleCrystalDiffractometer()
d = SingleCrystalDiffractometer(la2ni7(at=[0, 0, 0], relative="gonio_phi"), ei=14)
# with a file laid over it (read with a loader: YAML by default)
d = load("my_params.yaml")
d = load("my_params.yaml", loader=yaml_loader, ei=14)
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
