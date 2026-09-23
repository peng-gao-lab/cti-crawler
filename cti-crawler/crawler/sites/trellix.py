import threading
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..shared.reports import Report
from ..config_loader import SourceConfig
from ..shared.navigation.browser import load_more_pages


ITEM_SELECTOR = "div#mresults div.topiclisting"


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
            "#show-more-data",
            self.stop_event,
        ):
            soup = BeautifulSoup(html, "html.parser")
            for item in soup.select(ITEM_SELECTOR):
                link = item.find("a", href=True)
                if link:
                    yield Report(urljoin(self.source.base_url, link["href"]))
