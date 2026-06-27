from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets" / "legacy" / "manifest.json"
INDEX = ROOT / "index.html"

# Map the original JAFLEX asset filenames to their original content positions.
MATCHES = {
    "jaflex-logo": ["j-rogo.gif"],
    "hero-offshore": ["oil-platform-offshore-oil-production", "besthqwallpapers"],
    "coflexip-logo": ["cof-rogo-1.jpg", "cof-rogo"],
    "coflex-hose": ["scan.jpg"],
    "world-bridge-logo": ["d26c08922151d163d878ed2e47b540d5.png"],
    "wbi-interior-01": ["2b530e80c7d0de90885e285c5d798063.jpg"],
    "wbi-interior-02": ["120c549d7a51169ca7a58d264339d8a6-2048x1536.jpg", "120c549d7a51169ca7a58d264339d8a6"],
    "wbi-floating-roof": ["5659bbb04f98e68945cc4a3b9c7f93cc.png"],
    "wbi-roof-plant": ["20160830_104335-2048x1152.jpg", "20160830_104335"],
    "wbi-dome-desert": ["adr.jpg"],
    "wbi-dome-aerial-01": ["kakaotalk_20250723_154952986", "154952986"],
    "wbi-dome-aerial-02": ["kakaotalk_20250723_154531658", "154531658"],
}


def normalized(entry: dict) -> str:
    return unquote(f"{entry.get('source_url', '')} {entry.get('file', '')}").lower()


def find_path(entries: list[dict], fragments: list[str]) -> str | None:
    for fragment in fragments:
        needle = fragment.lower()
        for entry in entries:
            if needle in normalized(entry):
                return str(entry["file"])
    return None


def main() -> None:
    if not MANIFEST.exists():
        raise SystemExit("Legacy image manifest was not generated")

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = [entry for entry in data.get("downloaded", []) if entry.get("file")]
    html = INDEX.read_text(encoding="utf-8")

    missing: list[str] = []
    for key, fragments in MATCHES.items():
        path = find_path(entries, fragments)
        if not path:
            missing.append(key)
            continue
        pattern = rf'(<img\b[^>]*data-legacy-key=["\']{re.escape(key)}["\'][^>]*)(>)'

        def replace(match: re.Match[str]) -> str:
            tag = match.group(1)
            if re.search(r'\bsrc\s*=', tag):
                tag = re.sub(r'\bsrc\s*=\s*["\'][^"\']*["\']', f'src="{path}"', tag)
            else:
                tag += f' src="{path}"'
            return tag + match.group(2)

        html = re.sub(pattern, replace, html)

    INDEX.write_text(html, encoding="utf-8")
    print(f"Applied {len(MATCHES) - len(missing)} original image placements.")
    if missing:
        print("Images not found:", ", ".join(missing))


if __name__ == "__main__":
    main()
