"""The folders of the scripts: mcstas_input/, mcstas_output/ and output/ of the work folder, the
repository (MCSTAS_TO_SQE_WORKDIR if set), wherever the scripts run from: an Interactive Window
starts in scripts/, so the current folder would put them there."""

import os
from pathlib import Path

from mcstas_to_sqe import default_figures_dir
from mcstas_to_sqe.mcstas.run_folders import default_output_dir

WORK_DIR = Path(os.environ.get("MCSTAS_TO_SQE_WORKDIR") or Path(__file__).resolve().parents[1])
MCSTAS_DIR = default_output_dir(WORK_DIR)  # the simulation results: mcstas_output/
OUTPUT_DIR = default_figures_dir(WORK_DIR)  # the figures and peak lists: output/
