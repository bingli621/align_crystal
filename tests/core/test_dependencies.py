import subprocess
import sys


def test_core_imports_no_yaml_and_no_adapter():
    """The entities import no adapter (no YAML, no io, no McStas), no instrument and no sample."""
    code = (
        "import sys, align_crystal.core;"
        "bad = [m for m in sys.modules if m == 'yaml' or m.startswith(("
        "'align_crystal.io', 'align_crystal.mcstas', 'align_crystal.instruments',"
        " 'align_crystal.samples'))];"
        "assert not bad, bad"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
