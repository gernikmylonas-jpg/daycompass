"""The private HIDDEN_README must describe every file of the project and be up to date.
It lives in docs/hidden (git-ignored), so on a machine without that folder (CI) this test is skipped."""
import subprocess
import sys
from pathlib import Path

import pytest

BUILD = Path(__file__).resolve().parents[2] / "docs" / "hidden" / "build.py"


@pytest.mark.skipif(not BUILD.exists(), reason="docs/hidden is private and not present here")
def test_every_file_is_described_and_the_document_is_current():
    result = subprocess.run([sys.executable, str(BUILD), "--check"], capture_output=True, text=True, encoding="utf8")
    assert result.returncode == 0, result.stdout + result.stderr
