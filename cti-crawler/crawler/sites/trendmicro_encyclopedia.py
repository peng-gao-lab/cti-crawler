import re
import threading
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..shared.fetchers.document import FetchedDocument, document_from_response
from ..shared.reports import Report
from ..config_loader import SourceConfig


class Adapter:
    def __init__(self, source: SourceConfig, fetchers: dict, stop_event: threading.Event):
        self.source = source
        self.discovery_fetcher = fetchers[source.discovery]
        self.content_fetcher = fetchers[source.content]
        self.stop_event = stop_event

    def discover(self):
        start_url = self.source.start_urls[0]
        first_page = self.discovery_fetcher.get(start_url, wait_for="div.listContent")
        first_soup = BeautifulSoup(first_page.text, "html.parser")
        total_pages = self._total_pages(first_soup)
        total_pages = min(total_pages, self.discovery_fetcher.max_navigation_steps)
        seen = set()

        for page_number in range(1, total_pages + 1):
            if self.stop_event.is_set():
                break
            if page_number == 1:
                soup = first_soup
            else:
                page_url = f"{start_url.rstrip('/')}/page/{page_number}"
                response = self.discovery_fetcher.get(
                    page_url,
                    wait_for="div.listContent",
                )
                soup = BeautifulSoup(response.text, "html.parser")

            for link in soup.select("div.ContainerListTitle1 > a[href]"):
                url = urljoin(self.source.base_url, link["href"])
                if url not in seen:
                    seen.add(url)
                    yield Report(url)

    @staticmethod
    def _total_pages(soup: BeautifulSoup) -> int:
        pagination = soup.select_one("div.paginationContainer li")
        page_text = pagination.get_text(" ", strip=True) if pagination else ""
        match = re.search(r"of\s+(\d+)", page_text)
        return int(match.group(1)) if match else 1

    def fetch_content(self, url: str) -> FetchedDocument:
        response = self.content_fetcher.get(url, wait_for="section.TEArticle")
        return document_from_response(response, url)
