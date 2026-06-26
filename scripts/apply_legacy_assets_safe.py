from __future__ import annotations

import json
import re
from pathlib import Path

from apply_legacy_assets import ROOT, MANIFEST_PATH, INDEX_PATH, STYLE_PATH, img_html, pick, score


def replace_balanced_div(block: str, class_name: str, replacement: str) -> str:
    marker = f'<div class="{class_name}">'
    start = block.find(marker)
    if start < 0:
        return block
    token_pattern = re.compile(r'<div\b[^>]*>|</div>', re.I)
    depth = 0
    end = -1
    for match in token_pattern.finditer(block, start):
        token = match.group(0).lower()
        if token.startswith('<div'):
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                end = match.end()
                break
    if end < 0:
        return block
    return block[:start] + replacement + block[end:]


def replace_card(html: str, kicker: str, item: dict[str, object] | None, alt: str) -> str:
    if not item:
        return html
    article_pattern = re.compile(r'<article class="card reveal">.*?</article>', re.S)
    parts: list[str] = []
    cursor = 0
    for match in article_pattern.finditer(html):
        block = match.group(0)
        if f'<p class="kicker">{kicker}</p>' not in block:
            continue
        new_media = '<div class="card-art legacy-photo">' + img_html(item, alt) + '</div>'
        updated = replace_balanced_div(block, 'card-art', new_media)
        parts.append(html[cursor:match.start()])
        parts.append(updated)
        parts.append(html[match.end():])
        return ''.join(parts)
    return html


def main() -> None:
    if not MANIFEST_PATH.exists():
        raise SystemExit('Legacy image manifest was not created.')
    manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
    items = [
        item for item in manifest.get('downloaded', [])
        if (ROOT / str(item.get('file', ''))).exists() and int(item.get('bytes', 0)) >= 8000
    ]
    if not items:
        raise SystemExit('No usable legacy images were downloaded.')

    used: set[str] = set()
    hero = pick(items, ('main', 'slide', 'banner', 'hero'), used)
    technip = pick(items, ('technip', 'fmc', 'coflex', 'flexible', 'pipe'), used)
    worldbridge = pick(items, ('world', 'bridge', 'dome', 'roof', 'tank'), used)
    other = pick(items, ('product', 'item', 'equipment'), used)

    gallery_items: list[dict[str, object]] = []
    for item in sorted(items, key=score, reverse=True):
        file_path = str(item['file'])
        if file_path in used or score(item) <= 0:
            continue
        used.add(file_path)
        gallery_items.append(item)
        if len(gallery_items) >= 6:
            break

    html = INDEX_PATH.read_text(encoding='utf-8')

    if hero and 'legacy-hero-image' not in html:
        hero_markup = (
            '<div class="visual reveal legacy-photo">'
            + img_html(hero, 'JAFLEX既存ホームページで使用されていた代表画像', 'legacy-hero-image')
            + '<div class="visual-note"><strong>既存画像を継承</strong>'
              '現行ホームページで使用されていた画像をそのまま使用しています。</div>'
            + '</div>'
        )
        html = re.sub(
            r'<div class="visual reveal">.*?<div class="visual-note">.*?</div>\s*</div>',
            hero_markup,
            html,
            count=1,
            flags=re.S,
        )

    html = replace_card(html, 'TechnipFMC', technip, 'TechnipFMC製品の既存画像')
    html = replace_card(html, 'World Bridge Industrial', worldbridge, 'World Bridge製品の既存画像')
    html = replace_card(html, 'Other Products', other, 'その他の取扱製品の既存画像')

    if gallery_items and 'id="legacy-gallery"' not in html:
        figures = ''.join(
            '<figure class="legacy-gallery-item">'
            + img_html(item, 'JAFLEX既存ホームページ使用画像')
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
        html = html.replace(
            '<section class="section" id="company">',
            gallery + '<section class="section" id="company">',
            1,
        )

    INDEX_PATH.write_text(html, encoding='utf-8')

    css = STYLE_PATH.read_text(encoding='utf-8')
    additions = '''
.legacy-photo{background:#eef4f7}
.legacy-photo>img{display:block;width:100%;height:100%;object-fit:cover}
.visual.legacy-photo{min-height:420px}
.legacy-hero-image{aspect-ratio:1000/680}
.legacy-gallery{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.legacy-gallery-item{margin:0;overflow:hidden;border:1px solid var(--line);border-radius:14px;background:#fff;box-shadow:0 8px 28px rgba(18,59,93,.08);aspect-ratio:4/3}
.legacy-gallery-item img{width:100%;height:100%;display:block;object-fit:cover}
@media(max-width:760px){.legacy-gallery{grid-template-columns:1fr 1fr}.visual.legacy-photo{min-height:0}}
@media(max-width:480px){.legacy-gallery{grid-template-columns:1fr}}
'''
    if '.legacy-gallery{' not in css:
        STYLE_PATH.write_text(css + additions, encoding='utf-8')

    selection = {
        'hero': hero,
        'technip': technip,
        'worldbridge': worldbridge,
        'other': other,
        'gallery': gallery_items,
    }
    output = ROOT / 'assets' / 'legacy' / 'selection.json'
    output.write_text(json.dumps(selection, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Applied original JAFLEX images to {4 + len(gallery_items)} slots.')


if __name__ == '__main__':
    main()
