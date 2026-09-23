import threading
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..shared.reports import Report
from ..config_loader import SourceConfig


LANDING_SELECTOR = "a.grid.content-row-article, section.latest-content a.card"
PAGE_SELECTOR = ".content-listing-various__row a.grid.content-row-article"


class Adapter:
    def __init__(self, source: SourceConfig, fetchers: dict, stop_event: threading.Event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.stop_event = stop_event

    def discover(self):
        start_url = self.source.start_urls[0]
        self.fetcher.get(start_url, wait_for=LANDING_SELECTOR)
        previous_count = self.fetcher.element_count(LANDING_SELECTOR)
        if self.fetcher.click(
            ".content-listing-articles__button-show button[data-toggle='expand']"
        ):
            self.fetcher.wait_for_more(LANDING_SELECTOR, previous_count)

        seen = set()
        yield from self._new_urls(self.fetcher.current_html(), LANDING_SELECTOR, seen)

        last_page = min(400, self.fetcher.max_navigation_steps)
        for page_number in range(2, last_page + 1):
            if self.stop_event.is_set():
                break
            page_url = f"{start_url.rstrip('/')}/page/{page_number}/"
            response = self.fetcher.get(page_url, wait_for=PAGE_SELECTOR)
            urls = list(self._new_urls(response.text, PAGE_SELECTOR, seen))
            if not urls:
                break
            yield from urls

    def _new_urls(self, html: str, selector: str, seen: set[str]):
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.select(selector):
            url = urljoin(self.source.base_url, link["href"])
            if "csoonline.com/article/" in url and url not in seen:
                seen.add(url)
                yield Report(url)
