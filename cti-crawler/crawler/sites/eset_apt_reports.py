from urllib.parse import urljoin

from ..shared.reports import Report
from ..shared.navigation.linked import linked_pages


SERIES = "ESET APT Activity Report"


class Adapter:
    """Select the public APT PDF series from ESET's mixed report directory."""

    def __init__(self, source, fetchers, stop_event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.stop_event = stop_event

    def discover(self):
        for start_url in self.source.start_urls:
            for page_url, soup in linked_pages(
                self.fetcher, start_url, 'a.page-link[title=">"][href]', self.stop_event
            ):
                links = soup.select("a.file-download-text[href]")
                if not links:
                    raise ValueError(f"No ESET report downloads at {page_url}")
                for link in links:
                    title = link.get("download", "").strip()
                    if not title.startswith(SERIES + " "):
                        continue
                    url = urljoin(page_url, link["href"])
                    origin = {
                        "entry_url": start_url, "listing_url": page_url,
                        "series": SERIES, "title": title,
                    }
                    yield Report(url, [origin])
