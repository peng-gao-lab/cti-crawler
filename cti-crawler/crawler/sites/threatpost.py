import threading
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..shared.reports import Report
from ..config_loader import SourceConfig
from ..shared.navigation.browser import load_more_pages


ITEM_SELECTOR = "h2.c-card__title > a[href]"


class Adapter:
    def __init__(self, source: SourceConfig, fetchers: dict, stop_event: threading.Event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.stop_event = stop_event

    def discover(self):
        for html in load_more_pages(
            self.fetcher,
            self.source.start_urls[0],
            ITEM_SELECTOR,
            "#load_more_news",
            self.stop_event,
        ):
            soup = BeautifulSoup(html, "html.parser")
            for link in soup.select(ITEM_SELECTOR):
                yield Report(urljoin(self.source.base_url, link["href"]))
