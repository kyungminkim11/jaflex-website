import json
import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manifest = root / "assets" / "legacy" / "manifest.json"
index = root / "index.html"
style = root / "style.css"

data = json.loads(manifest.read_text(encoding="utf-8"))
images = [x for x in data.get("downloaded", []) if int(x.get("bytes", 0)) > 10000]
images.sort(key=lambda x: int(x.get("bytes", 0)), reverse=True)
if not images:
    raise SystemExit("No original JAFLEX photos were found")

html = index.read_text(encoding="utf-8")
paths = [x["file"] for x in images[:10]]

hero = f'<div class="visual reveal original-photo"><img src="{paths[0]}" alt="JAFLEX original website image"></div>'
html = re.sub(r'<div class="visual reveal">.*?</div>\s*</div>', hero, html, count=1, flags=re.S)

for path in paths[1:4]:
    photo = f'<div class="card-art original-photo"><img src="{path}" alt="JAFLEX original product image"></div>'
    html = re.sub(r'<div class="card-art">.*?</div>', photo, html, count=1, flags=re.S)

if 'class="original-gallery"' not in html and len(paths) > 4:
    gallery = ''.join(f'<img src="{path}" alt="JAFLEX original website image">' for path in paths[4:])
    section = f'<section class="section"><div class="wrap"><div class="head"><p class="eyebrow">Original Images</p><h2>既存ホームページの画像</h2></div><div class="original-gallery">{gallery}</div></div></section>'
    html = html.replace('<section class="section" id="company">', section + '<section class="section" id="company">', 1)

index.write_text(html, encoding="utf-8")
css = style.read_text(encoding="utf-8")
if '.original-photo' not in css:
    css += '\n.original-photo img{display:block;width:100%;height:100%;object-fit:cover}.original-gallery{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}.original-gallery img{width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:14px}@media(max-width:700px){.original-gallery{grid-template-columns:1fr 1fr}}\n'
    style.write_text(css, encoding="utf-8")
