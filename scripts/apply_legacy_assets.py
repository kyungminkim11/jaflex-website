from __future__ import annotations

import json
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "assets" / "legacy" / "manifest.json"
INDEX_PATH = ROOT / "index.html"
STYLE_PATH = ROOT / "style.css"

EXCLUDE_WORDS = {
    "logo", "icon", "favicon", "arrow", "button", "loading", "loader",
    "spinner", "blank", "pixel", "sns", "facebook", "twitter", "line",
}
PHOTO_WORDS = {
    "jpg", "jpeg", "photo", "image", "main", "slide", "banner", "hero",
    "coflex", "flexible", "pipe", "technip", "fmc", "world", "bridge",
    "dome", "roof", "tank", "product", "storage",
}


def image_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:64 * 1024]
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if data.startswith((b"GIF87a", b"GIF89a")) and len(data) >= 10:
        return struct.unpack("<HH", data[6:10])
    if data.startswith(b"\xff\xd8"):
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            i += 2
            if marker in {0xD8, 0xD9}:
                continue
            if i + 2 > len(data):
                break
            length = int.from_bytes(data[i:i + 2], "big")
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF} and i + 7 < len(data):
                height = int.from_bytes(data[i + 3:i + 5], "big")
                width = int.from_bytes(data[i + 5:i + 7], "big")
                return width, height
            i += max(length, 2)
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        if data[12:16] == b"VP8X" and len(data) >= 30:
            width = 1 + int.from_bytes(data[24:27], "little")
            height = 1 + int.from_bytes(data[27:30], "little")
            return width, height
    return 0, 0


def score(item: dict[str, object]) -> float:
    source = str(item.get("source_url", "")).lower()
    file_name = str(item.get("file", "")).lower()
    text = f"{source} {file_name}"
    path = ROOT / str(item["file"])
    width, height = image_size(path)
    area = width * height
    byte_size = int(item.get("bytes", 0))
    value = area + byte_size * 2
    if any(word in text for word in PHOTO_WORDS):
        value *= 1.5
    if any(word in text for word in EXCLUDE_WORDS):
        value *= 0.05
    if width and height:
        shortest = min(width, height)
        if shortest < 180:
            value *= 0.1
        ratio = max(width / max(height, 1), height / max(width, 1))
        if ratio > 6:
            value *= 0.25
    if path.suffix.lower() == ".svg":
        value *= 0.15
    return value


def pick(items: list[dict[str, object]], keywords: tuple[str, ...], used: set[str]) -> dict[str, object] | None:
    matched = []
    for item in items:
        file_path = str(item.get("file", ""))
        if file_path in used:
            continue
        haystack = f"{item.get('source_url', '')} {file_path}".lower()
        if keywords and not any(keyword in haystack for keyword in keywords):
            continue
        matched.append(item)
    if not matched and keywords:
        return pick(items, (), used)
    if not matched:
        return None
    chosen = max(matched, key=score)
    used.add(str(chosen["file"]))
    return chosen


def img_html(item: dict[str, object] | None, alt: str, css_class: str = "") -> str:
    if not item:
        return ""
    class_attr = f' class="{css_class}"' if css_class else ""
    return f'<img src="{item["file"]}" alt="{alt}"{class_attr} loading="lazy">'


def main() -> None:
    if not MANIFEST_PATH.exists():
        raise SystemExit("Legacy image manifest was not created.")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    items = [
        item for item in manifest.get("downloaded", [])
        if (ROOT / str(item.get("file", ""))).exists() and int(item.get("bytes", 0)) >= 8000
    ]
    if not items:
        raise SystemExit("No usable legacy images were downloaded.")

    used: set[str] = set()
    hero = pick(items, ("main", "slide", "banner", "hero"), used)
    technip = pick(items, ("technip", "fmc", "coflex", "flexible", "pipe"), used)
    worldbridge = pick(items, ("world", "bridge", "dome", "roof", "tank"), used)
    other = pick(items, ("product", "item", "equipment"), used)

    gallery_items: list[dict[str, object]] = []
    for item in sorted(items, key=score, reverse=True):
        file_path = str(item["file"])
        if file_path in used:
            continue
        if score(item) <= 0:
            continue
        used.add(file_path)
        gallery_items.append(item)
        if len(gallery_items) >= 6:
            break

    html = INDEX_PATH.read_text(encoding="utf-8")

    hero_markup = (
        '<div class="visual reveal legacy-photo">'
        + img_html(hero, "JAFLEX既存ホームページで使用されていた代表画像", "legacy-hero-image")
        + '<div class="visual-note"><strong>既存画像を継承</strong>現行ホームページで使用されていた画像をそのまま使用しています。</div>'
        + '</div>'
    )
    html = re.sub(
        r'<div class="visual reveal">.*?<div class="visual-note">.*?</div>\s*</div>',
        hero_markup,
        html,
        count=1,
        flags=re.S,
    )

    replacements = [
        ("TechnipFMC", technip, "TechnipFMC製品の既存画像"),
        ("World Bridge Industrial", worldbridge, "World Bridge製品の既存画像"),
        ("Other Products", other, "その他の取扱製品の既存画像"),
    ]
    for kicker, item, alt in replacements:
        if not item:
            continue
        pattern = (
            r'(<article class="card reveal">)'
            r'(<div class="card-art">.*?</div>)'
            r'(<div class="card-body"><p class="kicker">' + re.escape(kicker) + r'</p>)'
        )
        replacement = r'\1<div class="card-art legacy-photo">' + img_html(item, alt) + r'</div>\3'
        html = re.sub(pattern, replacement, html, count=1, flags=re.S)

    if gallery_items:
        figures = "".join(
            '<figure class="legacy-gallery-item">'
            + img_html(item, "JAFLEX既存ホームページ使用画像")
            + '</figure>'
            for item in gallery_items
        )
        gallery = (
            '<section class="section legacy-gallery-section" id="legacy-gallery">'
            '<div class="wrap">'
            '<div class="head reveal"><p class="eyebrow">Original Visuals</p>'
            '<h2>既存ホームページの画像</h2>'
            '<p>企業イメージの継続性を保つため、従来使用していた画像を引き継いでいます。</p></div>'
            f'<div class="legacy-gallery">{figures}</div>'
            '</div></section>'
        )
        html = html.replace('<section class="section" id="company">', gallery + '<section class="section" id="company">', 1)

    INDEX_PATH.write_text(html, encoding="utf-8")

    css = STYLE_PATH.read_text(encoding="utf-8")
    additions = """
.legacy-photo{background:#eef4f7}
.legacy-photo>img{display:block;width:100%;height:100%;object-fit:cover}
.visual.legacy-photo{min-height:420px}
.legacy-hero-image{aspect-ratio:1000/680}
.legacy-gallery{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.legacy-gallery-item{margin:0;overflow:hidden;border:1px solid var(--line);border-radius:14px;background:#fff;box-shadow:0 8px 28px rgba(18,59,93,.08);aspect-ratio:4/3}
.legacy-gallery-item img{width:100%;height:100%;display:block;object-fit:cover}
@media(max-width:760px){.legacy-gallery{grid-template-columns:1fr 1fr}.visual.legacy-photo{min-height:0}}
@media(max-width:480px){.legacy-gallery{grid-template-columns:1fr}}
"""
    if ".legacy-gallery{" not in css:
        STYLE_PATH.write_text(css + additions, encoding="utf-8")

    selection = {
        "hero": hero,
        "technip": technip,
        "worldbridge": worldbridge,
        "other": other,
        "gallery": gallery_items,
    }
    (ROOT / "assets" / "legacy" / "selection.json").write_text(
        json.dumps(selection, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Applied {4 + len(gallery_items)} legacy image slots.")


if __name__ == "__main__":
    main()
