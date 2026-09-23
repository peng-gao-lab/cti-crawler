import threading
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..shared.reports import Report
from ..config_loader import SourceConfig
from ..shared.navigation.browser import clicked_pages
from ..shared.navigation.linked import linked_pages


ITEM_SELECTOR = "div.body-post.clear > a[href]"


class Adapter:
    @staticmethod
    def pdf_content_selectors(url):
        return ("h1.story-title", "#articlebody")

    def __init__(self, source: SourceConfig, fetchers: dict, stop_event: threading.Event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.stop_event = stop_event

    def discover(self):
        if self.source.discovery == "http":
            yield from self._discover_http()
            return
        seen = set()
        pages = clicked_pages(
            self.fetcher,
            self.source.start_urls[0],
            ITEM_SELECTOR,
            "#Blog1_blog-pager-older-link",
            self.stop_event,
        )
        for html in pages:
            soup = BeautifulSoup(html, "html.parser")
            for link in soup.select(ITEM_SELECTOR):
                url = urljoin(self.source.base_url, link["href"])
                if url not in seen:
                    seen.add(url)
                    yield Report(url)

    def _discover_http(self):
        for start_url in self.source.start_urls:
            for page_url, soup in linked_pages(
                self.fetcher, start_url, "#Blog1_blog-pager-older-link[href]", self.stop_event
            ):
                links = soup.select(ITEM_SELECTOR)
                if not links:
                    raise ValueError(f"No The Hacker News article links at {page_url}")
                for link in links:
                    url = urljoin(page_url, link["href"])
                    heading = link.select_one(".home-title")
                    origin = {
                        "entry_url": start_url, "listing_url": page_url,
                        "topic": soup.h1.get_text(" ", strip=True) if soup.h1 else "",
                        "title": heading.get_text(" ", strip=True) if heading else link.get_text(" ", strip=True),
                    }
                    yield Report(url, [origin])
