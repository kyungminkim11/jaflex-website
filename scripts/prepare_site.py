from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"


def run(script: str) -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts" / script)], check=True)


def main() -> None:
    run("import_legacy_assets.py")
    html = INDEX.read_text(encoding="utf-8")
    if 'id="legacy-gallery"' not in html:
        run("apply_legacy_assets.py")
    else:
        print("Original JAFLEX images are already applied; skipping layout rewrite.")


if __name__ == "__main__":
    main()
