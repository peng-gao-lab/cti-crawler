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
        response = self.fetcher.get(self.source.start_urls[0])
        soup = BeautifulSoup(response.text, "html.parser")
        container = soup.select_one("div.blog_featured_category_list")
        if not container:
            raise ValueError("CrowdStrike category list was not found")

        category_urls = [
            urljoin(self.source.base_url, link["href"])
            for link in container.select("a.category-sidebar-link[href]")
        ]
        seen = set()
        for category_url in category_urls:
            if self.stop_event.is_set():
                break
            response = self.fetcher.get(category_url)
            soup = BeautifulSoup(response.text, "html.parser")
            for link in soup.select("div#blogAutoGenerationDiv h3 a[href]"):
                url = urljoin(self.source.base_url, link["href"])
                if url not in seen:
                    seen.add(url)
                    yield Report(url)
