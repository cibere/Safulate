from pathlib import Path

import pytest

from safulate import run_file

files_dir = Path(__file__).parent / "saf_files"
files = list(files_dir.glob("*.saf"))


@pytest.fixture(params=files, ids=[file.name for file in files])
def file(request: pytest.FixtureRequest) -> Path:
    return request.param


def test_files(file: Path) -> None:
    run_file(file)
