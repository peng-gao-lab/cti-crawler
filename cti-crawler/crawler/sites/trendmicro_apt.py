from urllib.parse import parse_qs, quote, urljoin, urlsplit, urlunsplit

from ..shared.reports import Report
from ..shared.naming import normalize_report_url


TOPIC = "APT & Targeted Attacks"
TAG = "trend-micro-research:threats/apt-and-targeted-attacks"


class Adapter:
    """Read the same filtered JSON index used by Trend Micro's research UI."""

    @staticmethod
    def pdf_content_selectors(url):
        return ("article.research-layout--wrapper",)

    def __init__(self, source, fetchers, stop_event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.stop_event = stop_event

    def discover(self):
        for entry_url in self.source.start_urls:
            if self.stop_event.is_set():
                return
            parts = urlsplit(entry_url)
            if parse_qs(parts.query).get("category") != [TAG]:
                raise ValueError("Trend Micro APT source requires the APT category filter")
            endpoint = urlunsplit((parts.scheme, parts.netloc,
                parts.path.removesuffix(".html") + ".tagSearch.json",
                "tags=" + quote(TAG, safe=":/"), ""))
            response = self.fetcher.get(endpoint, headers={
                "Referer": entry_url, "X-Requested-With": "XMLHttpRequest",
            })
            articles = response.json()["articles"]
            if not isinstance(articles, list):
                raise ValueError("Trend Micro returned an invalid article index")
            # The UI paginates this returned array locally; there is no next-page request.
            for article in articles:
                if self.stop_event.is_set():
                    return
                if article.get("primaryTag") != TOPIC or article.get("articleType") != "Research":
                    continue
                url = normalize_report_url(urljoin(entry_url, article["path"]))
                origin = {
                    "entry_url": entry_url, "listing_url": response.url,
                    "topic": TOPIC, "title": article["title"],
                    "article_type": article["articleType"], "tags": article.get("tags", []),
                }
                yield Report(url, [origin])
