import re
import threading

from bs4 import BeautifulSoup

from ..config_loader import SourceConfig
from ..shared.navigation.paged import numbered_pages


URL_PATTERN = re.compile(
    r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F]{2}))+"
)


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
            page_url=self._page_url,
        )

    @staticmethod
    def _page_url(start_url: str, page_number: int) -> str:
        return (
            f"{start_url.rstrip('/')}/cgi-bin/mt/mt-search.cgi"
            "?search=&IncludeBlogs=2&blog_id=2&archive_type=Index"
            f"&template_id=320&limit=10&page={page_number}"
        )

    @staticmethod
    def _extract_urls(html: str):
        soup = BeautifulSoup(html, "html.parser")
        for entry in soup.select(".entry"):
            if match := URL_PATTERN.search(str(entry)):
                yield match.group(0)
