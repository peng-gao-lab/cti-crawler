import threading
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..config_loader import SourceConfig
from ..shared.navigation.paged import numbered_pages


class Adapter:
    def __init__(self, source: SourceConfig, fetchers: dict, stop_event: threading.Event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.stop_event = stop_event

    def discover(self):
        yield from numbered_pages(
            self.fetcher,
            self.source.start_urls[0],
            self._extract_urls,
            self.stop_event,
            page_url=self._page_url,
        )

    @staticmethod
    def _page_url(start_url: str, page_number: int) -> str:
        base = start_url.rstrip("/")
        return f"{base}/page/{page_number}/?orderby=latest_first&db_posts_per_page=100"

    def _extract_urls(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.select("h3.c-card__title a[href]"):
            yield urljoin(self.source.base_url, link["href"])
