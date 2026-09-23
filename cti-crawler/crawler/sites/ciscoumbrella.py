import re
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
        )

    def _extract_urls(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        articles = soup.find_all("article", class_=re.compile(r"^post-\d+"))
        for article in articles:
            link = article.find("a", class_="entry-title-link", href=True)
            if link:
                yield urljoin(self.source.base_url, link["href"])

