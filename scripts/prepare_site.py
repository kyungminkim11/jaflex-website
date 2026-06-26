import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]


def run(name):
    subprocess.run([sys.executable, str(root / "scripts" / name)], check=True)


run("import_legacy_assets.py")
run("apply_original_photos.py")
