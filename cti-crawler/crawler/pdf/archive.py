"""Prepare a self-contained reading copy without revisiting the article URL."""
import base64
import json
import sqlite3
import threading
from concurrent.futures import Future
from functools import partial
from types import SimpleNamespace
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from ..shared.storage import FileStorage
from .markup import background_urls, preserve_image_size


VERSION = 3


def write_json(path, value):
    FileStorage(path.parent).write(path.name, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


def fingerprint(path):
    stat = path.stat()
    return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns, "archive_version": VERSION}


class ResourceCache:
    """Shared URL cache; short SQLite locks and one in-flight download per URL."""
    def __init__(self, path: Path, fetcher=None):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS resources (url TEXT PRIMARY KEY, data_uri TEXT NOT NULL)")
        self.fetcher = fetcher
        self.lock = threading.Lock()
        self.inflight = {}

    def with_headers(self, headers):
        # A per-article view prevents one publisher's headers leaking to another.
        return SimpleNamespace(image=partial(self.image, headers=dict(headers)))

    def image(self, url, referer, *, headers=None):
        if url.startswith("data:image/"):
            return url
        if urlsplit(url).scheme not in {"http", "https"}:
            raise ValueError(f"Unsupported image URL: {url}")
        if url.split("#", 1)[0] == referer.split("#", 1)[0]:
            raise ValueError(f"Image points to the article itself: {url}")
        with self.lock:
            row = self.db.execute("SELECT data_uri FROM resources WHERE url=?", (url,)).fetchone()
            if row:
                return row[0]
            if self.fetcher is None:
                raise ValueError(f"Image not archived (offline mode): {url}")
            future = self.inflight.get(url)
            owner = future is None
            if owner:
                future = self.inflight[url] = Future()
        if not owner:
            return future.result()
        try:
            response = self.fetcher.get(url, headers={"Referer": referer, **(headers or {})})
            media = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            if not media.startswith("image/") or not response.content:
                raise ValueError(f"Image returned empty or non-image content: {url} ({media})")
            result = f"data:{media};base64," + base64.b64encode(response.content).decode("ascii")
            with self.lock:
                self.db.execute("INSERT OR REPLACE INTO resources VALUES (?, ?)", (url, result))
                self.db.commit()
            future.set_result(result)
            return result
        except Exception as error:
            future.set_exception(error)
            raise
        finally:
            with self.lock:
                self.inflight.pop(url, None)

    def close(self):
        self.db.close()

    def clear(self):
        count = self.db.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
        if not count and not self.db.execute("PRAGMA freelist_count").fetchone()[0]:
            return {"resources_removed": 0, "cache_bytes_reclaimed": 0}
        page_size = self.db.execute("PRAGMA page_size").fetchone()[0]
        before = self.db.execute("PRAGMA page_count").fetchone()[0] * page_size
        self.db.execute("DELETE FROM resources")
        self.db.commit()
        # DELETE alone only frees SQLite pages internally, not disk space.
        self.db.execute("VACUUM")
        after = self.db.execute("PRAGMA page_count").fetchone()[0] * page_size
        return {"resources_removed": count, "cache_bytes_reclaimed": max(0, before - after)}


def resolve(base_url, url):
    # Defanged or otherwise malformed references (e.g. "example[.]com") are kept as written.
    try:
        return urljoin(base_url, url)
    except ValueError:
        return url


def image_url(image):
    # Prefer the actual lazy-loaded image over the placeholder in src.
    for key in ("data-src", "data-lazy-src", "data-original"):
        if image.get(key):
            return image[key]
    srcset = image.get("data-srcset") or image.get("srcset")
    if srcset:
        # Use the largest advertised width/density. Data URLs are taken from src.
        if "data:" in srcset:
            raise ValueError("Data URLs in srcset require explicit image src")
        candidates = []
        for candidate in srcset.split(","):
            parts = candidate.strip().split()
            if parts:
                size = float(parts[1][:-1]) if len(parts) > 1 else 1
                candidates.append((size, parts[0]))
        if candidates:
            return max(candidates)[1]
    return image.get("src")


def prepare_html(raw: bytes, base_url: str, cache: ResourceCache, selectors=()):
    soup = BeautifulSoup(raw, "html.parser")
    document_url = base_url
    stylesheets = [resolve(base_url, link["href"]) for link in soup.select('link[rel~="stylesheet"][href]')]
    if base := soup.find("base", href=True):
        base_url = resolve(base_url, base["href"])
    # Resolve every selector before moving any nodes: fallback must retain the full body.
    matches = [(selector, soup.select(selector)) for selector in selectors]
    boundary_fallback = [{"selector": selector, "matches": len(nodes)}
                         for selector, nodes in matches if len(nodes) != 1]
    if selectors and not boundary_fallback:
        body = soup.new_tag("div")
        for _, nodes in matches:
            body.append(nodes[0].extract())
    else:
        body = soup.body or soup
    title = soup.title.get_text() if soup.title else "Archived report"
    # A <title> emitted inside <body> by a streaming page is metadata, not report text.
    for tag in list(body.select("script, style, link, meta, base, template, title")):
        if tag.name in {"style", "title"} and tag.find_parent("svg"):
            continue
        tag.decompose()
    for tag in body.select("noscript"):
        tag.name = "div"
    # HTML parsers treat a non-SVG <image> start tag as <img>; the PDF renderer will too.
    for tag in body.find_all("image"):
        if not tag.find_parent("svg"):
            tag.name = "img"
    omitted = []
    omitted_embeds = []
    for tag in body.select("iframe, object, embed, canvas, video, audio"):
        if tag.parent is None:
            continue  # An enclosing embed has already been removed.
        # Explicit zero-area tracking frames are not visible report content.
        if tag.name == "iframe" and tag.get("width") == "0" and tag.get("height") == "0":
            omitted.append(tag.get("src", ""))
            tag.decompose()
            continue
        resource = tag.get("src") or tag.get("data")
        child = tag.find("source", src=True)
        if not resource and child:
            resource = child["src"]
        resource = resolve(base_url, resource) if resource else None
        omitted_embeds.append({"tag": tag.name, "url": resource})
        placeholder = soup.new_tag("p")
        placeholder.string = f"[Embedded {tag.name} omitted from this PDF]"
        if resource and urlsplit(resource).scheme in {"http", "https"}:
            link = soup.new_tag("a", href=resource)
            link.string = " Original embedded content"
            placeholder.append(link)
        tag.replace_with(placeholder)
    for tag in list(body.find_all(True)):
        style = tag.get("style", "")
        if tag.name in {'img', 'svg'} and not tag.find_parent('svg'):
            preserve_image_size(tag)
        backgrounds = background_urls(style) if "background" in style.lower() else []
        for background in backgrounds:
            picture = soup.new_tag("img", src=resolve(base_url, background.strip()))
            tag.append(picture)
        # Remove original layout (fixed heights, clipping, print-hidden text, etc.).
        for attr in ("style", "class", "hidden", "width", "height"):
            if tag.name == 'img' and attr in {'width', 'height'}:
                continue
            if tag.name not in {"svg", "path", "rect", "circle", "ellipse", "line", "polygon", "polyline", "g", "text", "use", "image"}:
                tag.attrs.pop(attr, None)
        if tag.name == "a" and tag.get("href"):
            tag["href"] = resolve(base_url, tag["href"])
        if tag.name == "details":
            tag["open"] = "open"
    # Decide on the page before any image request: placeholders must not count as text.
    if not body.get_text(strip=True):
        raise ValueError("No static HTML text; a dynamic page needs a site-specific fetcher")
    resources = []
    missing_images = []

    def unavailable(image, url, reason):
        alt = image.get("alt", "")
        missing_images.append({"url": url, "alt": alt, "reason": reason})
        placeholder = soup.new_tag("span")
        placeholder.string = "[Image unavailable" + (": " + alt if alt else "") + "]"
        image.replace_with(placeholder)

    for picture in body.select("picture"):
        if not picture.find("img"):
            unavailable(picture, None, "Picture has no fallback img")
            continue
        for source in picture.select("source"):
            source.decompose()
    for image in body.select("img"):
        absolute = None
        try:
            original = image_url(image)
            if not original:
                raise ValueError("Image has no static or supported lazy-load URL")
            absolute = urljoin(base_url, original)
            image["src"] = cache.image(absolute, document_url)
        except (ValueError, requests.RequestException) as error:
            unavailable(image, absolute, str(error))
            continue
        for attr in ("srcset", "data-srcset", "loading"):
            image.attrs.pop(attr, None)
        if not absolute.startswith("data:"):
            resources.append(absolute)
    # Code-copy widgets must print all their text, not a clipped form viewport.
    for field in body.select("textarea"):
        field.name = "pre"
    # Once presentation attributes have been removed, adjacent plain spans only
    # obstruct long-token wrapping (e.g. highlighted JSON split into many spans).
    # Keep anchors, language/direction attributes and SVG semantics intact.
    for span in body.select("span"):
        if not span.attrs and not span.find_parent("svg"):
            span.unwrap()
    result = BeautifulSoup("<!doctype html><html><head><meta charset='utf-8'><title></title></head><body></body></html>", "html.parser")
    result.title.string = title
    for child in list(body.contents):
        result.body.append(child.extract())
    return str(result), {"resources": sorted(set(resources)), "omitted_nonvisual_frames": omitted,
                         "omitted_embeds": omitted_embeds,
                         "missing_images": missing_images,
                         "boundary_fallback": boundary_fallback,
                         "omitted_stylesheets": stylesheets,
                         "content_selectors": list(selectors),
                         "content_scope": "Static text and available images in adapter-defined report sections (whole body if selectors absent or mismatched); missing media recorded; site CSS/scripts are not reproduced"}
