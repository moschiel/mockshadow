"""Identity of either a source checkout or a verified portable distribution."""
import json
from pathlib import Path
import subprocess

VERSION = "2.1.0"


def identity(root=None):
    root = Path(root or Path(__file__).parent)
    manifest = root / "distribution.json"
    if manifest.is_file():
        return json.loads(manifest.read_text(encoding="utf-8"))["source"]
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root, text=True).strip()
    return {"version": VERSION, "commit": git("rev-parse", "HEAD"),
            "dirty": bool(git("status", "--porcelain"))}
