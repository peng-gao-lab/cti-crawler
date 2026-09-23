from urllib.parse import urljoin

from ..shared.navigation.linked import linked_pages
from ..shared.reports import Report


SERIES = "Cybersecurity Threat Spotlight"


class Adapter:
    """Collect the mixed attack-activity series, pending semantic review."""

    def __init__(self, source, fetchers, stop_event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.stop_event = stop_event

    def discover(self):
        for entry_url in self.source.start_urls:
            # No next link means completion; do not probe nonexistent page numbers.
            for page_url, soup in linked_pages(
                self.fetcher, entry_url, 'a[rel~="next"][href], link[rel~="next"][href]',
                self.stop_event,
            ):
                heading = soup.select_one("main h1")
                if heading is None or heading.get_text(" ", strip=True) != SERIES:
                    raise ValueError(f"Cisco Threat Spotlight directory missing at {page_url}")
                links = soup.select("main article a.entry-title-link[href]")
                if not links:
                    raise ValueError(f"No Cisco Threat Spotlight articles at {page_url}")
                for link in links:
                    if self.stop_event.is_set():
                        return
                    yield Report(urljoin(page_url, link["href"]), [{
                        "entry_url": entry_url,
                        "listing_url": page_url,
                        "series": SERIES,
                        "title": link.get_text(" ", strip=True),
                    }])
