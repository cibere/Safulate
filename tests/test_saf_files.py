from safulate import run_file
import pytest
from pathlib import Path

files_dir = Path(__file__).parent / "saf_files"
files = list(files_dir.glob("*.saf"))

@pytest.fixture(params=files, ids=[file.name for file in files])
def file(request: pytest.FixtureRequest):
    return request.param

def test_files(file: Path) -> None:
    run_file(file)