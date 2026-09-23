import threading
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..shared.fetchers.document import FetchedDocument, document_from_response
from ..shared.reports import Report
from ..config_loader import SourceConfig


ITEM_SELECTOR = "div.table__col_title a[href]"


class Adapter:
    def __init__(self, source: SourceConfig, fetchers: dict, stop_event: threading.Event):
        self.source = source
        self.discovery_fetcher = fetchers[source.discovery]
        self.content_fetcher = fetchers[source.content]
        self.stop_event = stop_event

    def discover(self):
        start_url = self.source.start_urls[0]
        first_page = self.discovery_fetcher.get(start_url, wait_for=ITEM_SELECTOR)
        first_soup = BeautifulSoup(first_page.text, "html.parser")
        last_page = self._last_page(first_soup)
        if self.source.name == "kaspersky_threat" and last_page == 1:
            last_page = 100
        last_page = min(last_page, self.discovery_fetcher.max_navigation_steps)
        seen = set()

        for page_number in range(1, last_page + 1):
            if self.stop_event.is_set():
                break
            if page_number == 1:
                soup = first_soup
            else:
                response = self.discovery_fetcher.get(
                    f"{start_url}?paged={page_number}",
                    wait_for=ITEM_SELECTOR,
                )
                soup = BeautifulSoup(response.text, "html.parser")

            for link in soup.select(ITEM_SELECTOR):
                url = urljoin(self.source.base_url, link["href"])
                if url not in seen:
                    seen.add(url)
                    yield Report(url)

    @staticmethod
    def _last_page(soup: BeautifulSoup) -> int:
        pages = [
            int(item.get_text(strip=True))
            for item in soup.select("div.pagination__item")
            if item.get_text(strip=True).isdigit()
        ]
        return max(pages, default=1)

    def fetch_content(self, url: str) -> FetchedDocument:
        response = self.content_fetcher.get(url, wait_for="div.page__content")
        return document_from_response(response, url)
