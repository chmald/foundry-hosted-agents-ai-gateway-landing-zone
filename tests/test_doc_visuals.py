import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_docs_meet_visual_standard():
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "lint_doc_visuals.py"), "--root", str(ROOT), "--quiet"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout[-4000:]
