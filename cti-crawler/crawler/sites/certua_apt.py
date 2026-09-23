from html import escape
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from ..shared.discovery import DiscoveryError
from ..shared.fetchers.document import DocumentError, FetchedDocument
from ..shared.reports import Report


MALWARE_TAG = 30


class Adapter:
    """Use the public SPA index and materialize each article's HTML from its API."""

    def __init__(self, source, fetchers, stop_event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.content_fetcher = fetchers[source.content]
        self.stop_event = stop_event

    def discover(self):
        endpoint = urljoin(self.source.base_url, "/api/articles/byTags")
        try:
            page, total = 0, None
            seen = set()
            while (total is None or len(seen) < total) and not self.stop_event.is_set():
                response = self.fetcher.get(endpoint, params={"ids": MALWARE_TAG, "type": 1, "page": page},
                                            headers={"Accept": "application/json"})
                payload = response.json()
                total, items = payload["count"], payload["items"]
                if type(total) is not int or total < 0 or not isinstance(items, list) or (not items and total):
                    raise ValueError("CERT-UA returned an invalid or incomplete article index")
                added = 0
                for item in items:
                    if self.stop_event.is_set():
                        return
                    article_id = item["id"]
                    if type(article_id) is not int or article_id < 1:
                        raise ValueError("CERT-UA article ID missing or invalid")
                    if MALWARE_TAG not in [tag["id"] for tag in item["tags"]]:
                        raise ValueError("CERT-UA returned an article outside the malware tag")
                    if article_id in seen:
                        continue
                    seen.add(article_id)
                    added += 1
                    yield Report(urljoin(self.source.base_url, f"/article/{article_id}"), [{
                        "entry_url": self.source.start_urls[0], "listing_url": response.url,
                        "listing_page": page, "article_id": article_id,
                        "title": item["title"], "published_at": item["date"],
                        "tags": item["tags"], "review_status": "unreviewed",
                    }])
                if items and not added:
                    raise ValueError("CERT-UA returned repeated article results")
                page += 1
        except InterruptedError:
            raise
        except Exception as error:
            raise DiscoveryError(endpoint, error) from error

    def fetch_content(self, url):
        target = urlsplit(url)
        article_id = target.path.removeprefix("/article/").rstrip("/")
        if (target.scheme != "https" or target.hostname != urlsplit(self.source.base_url).hostname
                or not target.path.startswith("/article/") or not article_id.isdecimal()):
            raise ValueError(f"Unexpected CERT-UA article URL: {url}")
        response = self.content_fetcher.get(
            urljoin(self.source.base_url, "/api/articles/byId"),
            params={"id": int(article_id), "lang": "uk"}, headers={"Accept": "application/json"},
        )
        try:
            payload = response.json()
            if payload["id"] != int(article_id):
                raise ValueError("CERT-UA API returned a different article")
            title, body = payload["title"], payload["text"]
            if not isinstance(title, str) or not title.strip() or not isinstance(body, str):
                raise ValueError("CERT-UA article title or body missing")
            if not BeautifulSoup(body, "html.parser").get_text(" ", strip=True):
                raise ValueError("CERT-UA article body is empty")
            if MALWARE_TAG not in [tag["id"] for tag in payload["tags"]]:
                raise ValueError("CERT-UA article no longer has the malware tag")
        except (ValueError, KeyError, TypeError) as error:
            raise DocumentError(str(error), response, reason="invalid_article") from error
        # Preserve the API's entire body, including data-URI images and tables.
        # No article-shell request, image stripping, or browser rendering is needed.
        html = (
            '<!DOCTYPE html><html lang="uk"><head><meta charset="utf-8">'
            f'<base href="{escape(url, quote=True)}"><title>{escape(title)}</title>'
            f'<meta name="source-api" content="{escape(response.url, quote=True)}">'
            '</head><body><main><article>'
            f'<h1>{escape(title)}</h1><p>{escape(str(payload.get("date", "")))}</p>'
            f'<p><a href="{escape(url, quote=True)}">CERT-UA source</a></p>'
            f'<div class="entry-content">{body}</div>'
            '</article></main></body></html>'
        )
        return FetchedDocument(html.encode("utf-8"), ".html", response.url, "text/html")
