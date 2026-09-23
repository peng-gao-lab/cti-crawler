import threading
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..shared.reports import Report
from ..config_loader import SourceConfig
from ..shared.navigation.browser import load_more_pages


ITEM_SELECTOR = "article.grid-item"


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
            ".load-more-btn",
            self.stop_event,
        ):
            soup = BeautifulSoup(html, "html.parser")
            seen = set()

            featured = soup.select_one("div.promotional-content h2.article-title a[href]")
            if featured:
                url = urljoin(self.source.base_url, featured["href"])
                seen.add(url)
                yield Report(url)

            for link in soup.select("article.grid-item h3.heading a[href]"):
                url = urljoin(self.source.base_url, link["href"])
                if url not in seen:
                    seen.add(url)
                    yield Report(url)
