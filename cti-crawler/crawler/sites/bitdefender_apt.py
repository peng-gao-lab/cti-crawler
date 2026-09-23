from urllib.parse import urljoin

from ..shared.navigation.linked import linked_pages
from ..shared.reports import Report


CARD_SELECTOR = '.tw-container[class~="md:tw-grid-cols-3"] > div'
NEXT_SELECTOR = 'a[href*="?page="]:-soup-contains("›")'
REQUIRED_TAGS = {"Advanced Persistent Threats", "Threat Research"}
EXCLUDED_TAG = "Cybersecurity Awareness"


class Adapter:
    """Collect Business Insights attack research using publisher card tags."""

    def __init__(self, source, fetchers, stop_event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.stop_event = stop_event

    def discover(self):
        for entry_url in self.source.start_urls:
            # An unqualified page is not the end: follow the unfiltered listing.
            for page_url, soup in linked_pages(
                self.fetcher, entry_url, NEXT_SELECTOR, self.stop_event
            ):
                cards = soup.select(CARD_SELECTOR)
                if not cards:
                    raise ValueError(f"No Bitdefender report cards at {page_url}")
                for card in cards:
                    if self.stop_event.is_set():
                        return
                    heading = card.select_one("h3")
                    link = heading.find_parent("a", href=True) if heading else None
                    if link is None:
                        raise ValueError(f"Bitdefender report card has no title link at {page_url}")
                    tags = [a.get_text(" ", strip=True) for a in card.select(
                        'a[href*="/businessinsights/tag/"]'
                    )]
                    if not REQUIRED_TAGS.issubset(tags) or EXCLUDED_TAG in tags:
                        continue
                    yield Report(urljoin(page_url, link["href"]), [{
                        "entry_url": entry_url,
                        "listing_url": page_url,
                        "title": heading.get_text(" ", strip=True),
                        "tags": tags,
                        "excluded_tags": [EXCLUDED_TAG],
                    }])
