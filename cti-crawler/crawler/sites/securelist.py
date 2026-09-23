import threading
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..shared.reports import Report
from ..config_loader import SourceConfig
from ..shared.navigation.paged import numbered_pages
from ..shared.navigation.linked import linked_pages


class Adapter:
    def __init__(self, source: SourceConfig, fetchers: dict, stop_event: threading.Event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.stop_event = stop_event

    def discover(self):
        if self.source.source_family in {"vendor_apt", "activity_reports"}:
            yield from self._discover_listing()
            return
        yield from numbered_pages(
            self.fetcher,
            self.source.start_urls[0],
            self._extract_urls,
            self.stop_event,
        )

    def _discover_listing(self):
        for start_url in self.source.start_urls:
            for page_url, soup in linked_pages(
                self.fetcher, start_url, "a.next.page-numbers[href]", self.stop_event
            ):
                links = soup.select(".js-post-items a.c-card__link[href]")
                if not links:
                    raise ValueError(f"No Securelist report links at {page_url}")
                for link in links:
                    url = urljoin(page_url, link["href"])
                    origin = {
                        "entry_url": start_url, "listing_url": page_url,
                        "topic": "APT reports" if self.source.source_family == "vendor_apt" else "Archive",
                        "title": link.get_text(" ", strip=True),
                    }
                    yield Report(url, [origin])

    def _extract_urls(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.select("a.c-card__link[href]"):
            yield urljoin(self.source.base_url, link["href"])
