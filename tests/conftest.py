import pytest


@pytest.fixture
def write_yaml(tmp_path):
    """write_yaml(text) -> path of a YAML file with that text."""

    def write(text, name="config.yaml"):
        path = tmp_path / name
        path.write_text(text)
        return path

    return write
