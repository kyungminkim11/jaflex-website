from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import time
from collections import deque
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "legacy"
MANIFEST = OUTPUT / "manifest.json"

START_URLS = [
    "https://jaflex.netlify.app/",
    "https://jaflex.netlify.app/jaflex.co.jp/",
    "https://jaflex.netlify.app/jaflex.co.jp/%E5%8F%96%E6%89%B1%E5%95%86%E5%93%81/",
    "https://jaflex.netlify.app/jaflex.co.jp/%E4%BC%9A%E7%A4%BE%E6%A1%88%E5%86%85/",
    "https://jaflex.netlify.app/jaflex.co.jp/%E4%B8%BB%E3%81%AA%E5%8F%96%E5%BC%95%E5%85%88/",
]

ALLOWED_HOSTS = {"jaflex.netlify.app", "jaflex.co.jp", "www.jaflex.co.jp"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".avif"}
CSS_EXTS = {".css"}
MAX_PAGES = 80
MAX_DEPTH = 4


def fetch(url: str, timeout: int = 25) -> tuple[bytes, str]:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; JAFLEX-Renewal-Importer/1.0)",
            "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read(), response.headers.get_content_type()


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: set[str] = set()
        self.assets: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value for key, value in attrs if value}
        if tag == "a" and values.get("href"):
            self.links.add(values["href"])
        for key in ("src", "data-src", "data-lazy-src", "poster"):
            if values.get(key):
                self.assets.add(values[key])
        for key in ("srcset", "data-srcset"):
            if values.get(key):
                for candidate in values[key].split(","):
                    src = candidate.strip().split(" ")[0]
                    if src:
                        self.assets.add(src)
        style = values.get("style", "")
        for found in re.findall(r"url\(['\"]?([^'\")]+)", style):
            self.assets.add(found)


def normalize(url: str, base: str) -> str | None:
    value = url.strip()
    if not value or value.startswith(("data:", "mailto:", "tel:", "javascript:", "#")):
        return None
    absolute = urljoin(base, value)
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"}:
        return None
    return parsed._replace(fragment="").geturl()


def safe_name(url: str, content_type: str) -> str:
    parsed = urlparse(url)
    original = Path(unquote(parsed.path)).name
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", original).strip("-._")
    suffix = Path(stem).suffix.lower()
    if suffix not in IMAGE_EXTS:
        guessed = mimetypes.guess_extension(content_type) or ".bin"
        if guessed == ".jpe":
            guessed = ".jpg"
        stem = (Path(stem).stem or "asset") + guessed
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    return f"{digest}-{stem or 'asset'}"


def extract_css_assets(data: bytes, base: str) -> set[str]:
    text = data.decode("utf-8", errors="ignore")
    found: set[str] = set()
    for raw in re.findall(r"url\(['\"]?([^'\")]+)", text):
        normalized = normalize(raw, base)
        if normalized:
            found.add(normalized)
    return found


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    queue: deque[tuple[str, int]] = deque((url, 0) for url in START_URLS)
    visited_pages: set[str] = set()
    asset_urls: set[str] = set()
    css_urls: set[str] = set()
    errors: list[dict[str, str]] = []

    while queue and len(visited_pages) < MAX_PAGES:
        url, depth = queue.popleft()
        if url in visited_pages or depth > MAX_DEPTH:
            continue
        parsed = urlparse(url)
        if parsed.hostname not in ALLOWED_HOSTS:
            continue
        try:
            data, content_type = fetch(url)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            errors.append({"url": url, "error": str(exc)})
            continue
        visited_pages.add(url)
        if content_type == "text/css" or Path(parsed.path).suffix.lower() in CSS_EXTS:
            css_urls.add(url)
            asset_urls.update(extract_css_assets(data, url))
            continue
        if content_type not in {"text/html", "application/xhtml+xml"}:
            if content_type.startswith("image/"):
                asset_urls.add(url)
            continue
        parser = PageParser()
        parser.feed(data.decode("utf-8", errors="ignore"))
        for raw in parser.assets:
            normalized = normalize(raw, url)
            if normalized:
                suffix = Path(urlparse(normalized).path).suffix.lower()
                if suffix == ".css":
                    css_urls.add(normalized)
                else:
                    asset_urls.add(normalized)
        for raw in parser.links:
            normalized = normalize(raw, url)
            if not normalized:
                continue
            target = urlparse(normalized)
            if target.hostname in ALLOWED_HOSTS:
                suffix = Path(target.path).suffix.lower()
                if suffix in IMAGE_EXTS:
                    asset_urls.add(normalized)
                elif suffix == ".css":
                    css_urls.add(normalized)
                elif suffix in {"", ".html", ".htm", ".php"}:
                    queue.append((normalized, depth + 1))
        time.sleep(0.08)

    for css_url in sorted(css_urls):
        try:
            data, _ = fetch(css_url)
            asset_urls.update(extract_css_assets(data, css_url))
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            errors.append({"url": css_url, "error": str(exc)})

    downloaded: list[dict[str, object]] = []
    for url in sorted(asset_urls):
        try:
            data, content_type = fetch(url)
            if not content_type.startswith("image/"):
                suffix = Path(urlparse(url).path).suffix.lower()
                if suffix not in IMAGE_EXTS:
                    continue
            if len(data) < 100:
                continue
            filename = safe_name(url, content_type)
            target = OUTPUT / filename
            target.write_bytes(data)
            downloaded.append(
                {
                    "source_url": url,
                    "file": f"assets/legacy/{filename}",
                    "content_type": content_type,
                    "bytes": len(data),
                }
            )
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            errors.append({"url": url, "error": str(exc)})

    manifest = {
        "start_urls": START_URLS,
        "pages_visited": sorted(visited_pages),
        "downloaded": downloaded,
        "errors": errors,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Visited {len(visited_pages)} pages and downloaded {len(downloaded)} assets.")


if __name__ == "__main__":
    main()
