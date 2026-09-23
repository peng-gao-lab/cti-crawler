from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from ..shared.discovery import DiscoveryError
from ..shared.reports import Report


CATEGORY = "advanced-persistent-threats"


class Adapter:
    """Read the APT cards embedded in Group-IB's client-filtered blog list."""

    def __init__(self, source, fetchers, stop_event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.stop_event = stop_event

    def discover(self):
        for entry_url in self.source.start_urls:
            page_url = entry_url
            try:
                if self.stop_event.is_set():
                    return
                response = self.fetcher.get(entry_url)
                page_url = response.url
                soup = BeautifulSoup(response.text, "html.parser")
                # The publisher repeats this id on cards; select all, not find(id).
                cards = soup.select(f'.blogpost-card[id="{CATEGORY}"]')
                if not cards:
                    raise ValueError(f"Group-IB APT cards missing at {page_url}")
                for card in cards:
                    if self.stop_event.is_set():
                        return
                    title = card.select_one(".blogpost-card__title")
                    if not card.get("href") or title is None:
                        raise ValueError(f"Group-IB APT card lacks title or URL at {page_url}")
                    url = urljoin(page_url, card["href"])
                    target = urlsplit(url)
                    if (target.scheme != "https" or target.hostname != urlsplit(self.source.base_url).hostname
                            or not target.path.startswith("/blog/") or target.path == "/blog/"):
                        raise ValueError(f"Unexpected Group-IB article URL: {url}")
                    meta = card.select_one(".blogpost-card__meta")
                    yield Report(url, [{
                        "entry_url": entry_url, "listing_url": page_url,
                        "category": CATEGORY, "title": title.get_text(" ", strip=True),
                        "card_metadata": meta.get_text(" ", strip=True) if meta else "",
                    }])
            except InterruptedError:
                raise
            except Exception as error:
                raise DiscoveryError(page_url, error) from error
