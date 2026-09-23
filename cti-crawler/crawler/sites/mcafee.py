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
        response = self.discovery_fetcher.get(
            start_url,
            wait_for="div.topics h3 a",
        )
        soup = BeautifulSoup(response.text, "html.parser")
        category_urls = list(
            dict.fromkeys(
                urljoin(self.source.base_url, link["href"])
                for link in soup.select("div.topics h3 a[href]")
            )
        )
        seen = set()

        for category_url in category_urls:
            for page_number in range(1, self.discovery_fetcher.max_navigation_steps + 1):
                if self.stop_event.is_set():
                    return
                page_url = (
                    category_url
                    if page_number == 1
                    else f"{category_url.rstrip('/')}/page/{page_number}/"
                )
                response = self.discovery_fetcher.get(
                    page_url,
                    wait_for="div.left-main-content",
                )

                soup = BeautifulSoup(response.text, "html.parser")
                links = soup.select("h5.card-title a[href]")
                if not links:
                    break
                for link in links:
                    url = urljoin(self.source.base_url, link["href"])
                    if url not in seen:
                        seen.add(url)
                        yield Report(url)

    def fetch_content(self, url: str) -> FetchedDocument:
        response = self.content_fetcher.get(url, wait_for="article")
        return document_from_response(response, url)
