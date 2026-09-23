import threading
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..shared.reports import Report
from ..config_loader import SourceConfig
from ..shared.navigation.browser import load_more_pages


class Adapter:
    def __init__(self, source: SourceConfig, fetchers: dict, stop_event: threading.Event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.stop_event = stop_event

    def discover(self):
        for html in load_more_pages(
            self.fetcher,
            self.source.start_urls[0],
            "a.blog-post-teaser__link-wrapper",
            ".blog-post-feed__load-more--button",
            self.stop_event,
        ):
            soup = BeautifulSoup(html, "html.parser")
            for link in soup.select("a.blog-post-teaser__link-wrapper[href]"):
                yield Report(urljoin(self.source.base_url, link["href"]))
