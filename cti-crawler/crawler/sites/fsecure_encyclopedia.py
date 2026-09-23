import threading
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..shared.reports import Report
from ..config_loader import SourceConfig


class Adapter:
    def __init__(self, source: SourceConfig, fetchers: dict, stop_event: threading.Event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.stop_event = stop_event

    def discover(self):
        start_url = self.source.start_urls[0]
        response = self.fetcher.get(
            start_url,
            wait_for='ul[class^="page_indexlist_"] li',
        )
        soup = BeautifulSoup(response.text, "html.parser")
        index = soup.select_one('ul[class^="page_indexlist_"]')
        if not index:
            raise ValueError(f"No threat index found at {start_url}")

        for link in index.select("li a[href]"):
            yield Report(urljoin(start_url, link["href"]))
