import threading
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..shared.reports import Report
from ..config_loader import SourceConfig
from ..shared.fetchers.document import FetchedDocument, document_from_response
from ..shared.navigation.paged import numbered_pages


RESEARCH_TAG = "ESET Research"


class Adapter:
    def __init__(self, source: SourceConfig, fetchers: dict, stop_event: threading.Event):
        self.source = source
        self.discovery_fetcher = fetchers[source.discovery]
        self.content_fetcher = fetchers[source.content]
        self.stop_event = stop_event

    def discover(self):
        if self.source.source_family == "activity_reports":
            yield from self._discover_research()
            return
        yield from numbered_pages(
            self.discovery_fetcher,
            self.source.start_urls[0],
            self._extract_urls,
            self.stop_event,
            page_url=lambda start, page: f"{start}?page={page}",
        )

    def _discover_research(self):
        # The category renders no next link (pagination is client-side). Numbered pages are
        # served at ?page=N (the /page/N/ form redirects there). Past the category's last page
        # the site keeps serving cards from the whole blog (privacy, scams, videos ...), so only
        # cards tagged "ESET Research" count and a page without such cards ends the walk; one
        # empty page in the middle is tolerated.
        for start_url in self.source.start_urls:
            for report in numbered_pages(
                self.discovery_fetcher, start_url,
                lambda html, start=start_url: self._extract_research_urls(html, start),
                self.stop_event,
                page_url=lambda start, page: f"{start}?page={page}",
                empty_page_tolerance=1,
                page_delay=2.0,  # the category answered 429 to ~45 listing requests in 30 s
            ):
                report.origins[0]["topic"] = "ESET Research"
                yield report

    def _extract_research_urls(self, html: str, start_url: str):
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.select("div.article-card > a[href]"):
            tags = {tag.get_text(" ", strip=True) for tag in link.select(".article-tag")}
            if RESEARCH_TAG in tags:
                yield urljoin(start_url, link["href"])

    def _extract_urls(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        for card in soup.select("div.article-list-card"):
            link = card.find("a", href=True)
            if link:
                yield urljoin(self.source.base_url, link["href"])

    def fetch_content(self, url: str) -> FetchedDocument:
        if self.source.content == "http":
            return document_from_response(self.content_fetcher.get(url), url)
        response = self.content_fetcher.get(url, wait_for="div.article-body")
        return document_from_response(response, url)
