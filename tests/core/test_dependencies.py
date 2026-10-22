import subprocess
import sys


def test_core_imports_no_yaml_and_no_adapter():
    """The entities import no adapter (no YAML, no io, no McStas), no instrument and no sample."""
    code = (
        "import sys, mcstas_to_sqe.core;"
        "bad = [m for m in sys.modules if m == 'yaml' or m.startswith(("
        "'mcstas_to_sqe.io', 'mcstas_to_sqe.mcstas', 'mcstas_to_sqe.instruments',"
        " 'mcstas_to_sqe.samples'))];"
        "assert not bad, bad"
    )
    subprocess.run([sys.executable, "-c", code], check=True)
