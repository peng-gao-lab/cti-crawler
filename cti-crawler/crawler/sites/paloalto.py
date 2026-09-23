import threading
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from ..shared.fetchers.document import FetchedDocument, document_from_response
from ..shared.reports import Report
from ..config_loader import SourceConfig
from ..shared.navigation.browser import load_more_pages


ITEM_SELECTOR = "div.article-card h2.title a[href]"


class Adapter:
    def __init__(self, source: SourceConfig, fetchers: dict, stop_event: threading.Event):
        self.source = source
        self.discovery_fetcher = fetchers[source.discovery]
        self.content_fetcher = fetchers[source.content]
        self.stop_event = stop_event

    def discover(self):
        response = self.discovery_fetcher.get(
            self.source.start_urls[0],
            wait_for="a.button-link",
        )
        soup = BeautifulSoup(response.text, "html.parser")
        source_host = urlsplit(self.source.base_url).netloc
        category_urls = list(
            dict.fromkeys(
                urljoin(self.source.base_url, link["href"])
                for link in soup.select("a.button-link[href]")
                if "See all" in link.get_text(" ", strip=True)
            )
        )
        seen = set()

        for category_url in category_urls:
            if self.stop_event.is_set():
                break
            if urlsplit(category_url).netloc != source_host:
                continue
            for html in load_more_pages(
                self.discovery_fetcher,
                category_url,
                ITEM_SELECTOR,
                "a",
                self.stop_event,
                button_text="Load more blogs",
            ):
                category_soup = BeautifulSoup(html, "html.parser")
                for link in category_soup.select(ITEM_SELECTOR):
                    url = urljoin(self.source.base_url, link["href"])
                    if url not in seen:
                        seen.add(url)
                        yield Report(url)

    def fetch_content(self, url: str) -> FetchedDocument:
        self.content_fetcher.get(url)
        self.content_fetcher.click(
            ".onetrust-close-btn-handler",
            timeout_seconds=10,
        )
        self.content_fetcher.wait_for(".article-container > section.article")
        return document_from_response(self.content_fetcher.current_response(), url)
