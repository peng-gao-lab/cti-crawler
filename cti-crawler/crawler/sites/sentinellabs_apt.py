from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from ..shared.discovery import DiscoveryError
from ..shared.fetchers.document import DocumentError, document_from_response
from ..shared.navigation.linked import linked_pages
from ..shared.reports import Report


class Adapter:
    """Discover only the APT archive's main cards, excluding fixed sidebar posts."""

    def __init__(self, source, fetchers, stop_event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.content_fetcher = fetchers[source.content]
        self.stop_event = stop_event

    def discover(self):
        for entry_url in self.source.start_urls:
            for page_url, soup in linked_pages(
                self.fetcher, entry_url, "a.next.page-numbers[href]", self.stop_event
            ):
                heading = soup.find("h1")
                cards = soup.select("#primary article.labs_category-advanced-persistent-threat")
                if heading is None or heading.get_text(" ", strip=True) != "Advanced Persistent Threat" or not cards:
                    raise DiscoveryError(page_url, ValueError("SentinelLabs APT archive missing"))
                for card in cards:
                    if self.stop_event.is_set():
                        return
                    link = card.select_one("a.title[href]")
                    if link is None:
                        raise DiscoveryError(page_url, ValueError("SentinelLabs title link missing"))
                    url = urljoin(page_url, link["href"])
                    target = urlsplit(url)
                    if (target.scheme != "https" or target.hostname != urlsplit(self.source.base_url).hostname
                            or not target.path.startswith("/labs/")):
                        raise DiscoveryError(page_url, ValueError(f"Unexpected SentinelLabs article URL: {url}"))
                    date = card.select_one("time[datetime]")
                    yield Report(url, [{
                        "entry_url": entry_url, "listing_url": page_url,
                        "title": link.get_text(" ", strip=True),
                        "published_at": date["datetime"] if date else None,
                        "category": "advanced-persistent-threat", "review_status": "unreviewed",
                    }])

    def fetch_content(self, url):
        response = self.content_fetcher.get(url)
        document = document_from_response(response, url)
        soup = BeautifulSoup(response.content, "html.parser")
        body = soup.select_one("article .entry-content")
        if body is None or not body.get_text(" ", strip=True):
            raise DocumentError("SentinelLabs article body missing", response, reason="missing_article_body")
        lead = body.get_text(" ", strip=True)[:500].lower()
        if lead.startswith(("editor’s note:", "editor's note:")) and "removed the article" in lead:
            raise DocumentError("SentinelLabs article replaced by a removal notice", response, reason="removed_article")
        return document
