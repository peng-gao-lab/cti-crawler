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
            page_url=lambda start, page: f"{start}?page={page}",
        )

    def _extract_urls(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        for heading in soup.find_all("h3"):
            link = heading.find_parent("a", href=True)
            if link and link["href"].startswith("/"):
                yield urljoin(self.source.base_url, link["href"])
