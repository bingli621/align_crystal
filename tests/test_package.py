from pathlib import Path

import mcstas_to_sqe
from mcstas_to_sqe import default_figures_dir


def test_version():
    assert mcstas_to_sqe.__version__


def test_the_figures_are_in_the_work_folder(tmp_path, monkeypatch):
    monkeypatch.delenv("MCSTAS_TO_SQE_WORKDIR", raising=False)
    monkeypatch.chdir(tmp_path)
    assert default_figures_dir() == tmp_path / "output"  # the current folder
    assert default_figures_dir("elsewhere") == Path("elsewhere") / "output"
    monkeypatch.setenv("MCSTAS_TO_SQE_WORKDIR", str(tmp_path / "scratch"))
    assert default_figures_dir() == tmp_path / "scratch" / "output"
