from urllib.parse import urljoin

from ..shared.navigation.linked import linked_pages
from ..shared.reports import Report


CATEGORY = "Technical"


class Adapter:
    """Collect Seqrite Labs' Technical category (attack-activity write-ups mixed with malware analyses); content review is deferred."""

    def __init__(self, source, fetchers, stop_event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.stop_event = stop_event

    def discover(self):
        for entry_url in self.source.start_urls:
            # WordPress category listing: follow the real <link rel="next"> only; no page-number guessing.
            for page_url, soup in linked_pages(
                self.fetcher, entry_url, 'link[rel~="next"][href], a.next[href]',
                self.stop_event,
            ):
                canonical = soup.select_one('link[rel="canonical"][href]')
                if canonical is None or "/blog/category/technical/" not in canonical["href"]:
                    raise ValueError(f"Seqrite Technical category listing missing at {page_url}")
                posts = soup.select("article.type-post")
                if not posts:
                    raise ValueError(f"No Seqrite Technical posts at {page_url}")
                for post in posts:
                    if self.stop_event.is_set():
                        return
                    if "category-technical" not in (post.get("class") or []):
                        continue  # a card from another category rendered on the page
                    link = post.select_one("h2.entry-title a[href]")
                    if link is None:
                        continue
                    yield Report(urljoin(page_url, link["href"]), [{
                        "entry_url": entry_url,
                        "listing_url": page_url,
                        "category": CATEGORY,
                        "title": link.get("title") or link.get_text(" ", strip=True),
                    }])
