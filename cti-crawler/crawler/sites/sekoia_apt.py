from urllib.parse import urljoin, urlsplit

from ..shared.discovery import DiscoveryError
from ..shared.navigation.linked import linked_pages
from ..shared.reports import Report


class Adapter:
    """Read the APT collection and its actual Webflow next links."""

    def __init__(self, source, fetchers, stop_event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.stop_event = stop_event

    def discover(self):
        for entry_url in self.source.start_urls:
            seen = set()
            for page_url, soup in linked_pages(
                self.fetcher, entry_url,
                ".blog-cat_list-wrap a.w-pagination-next[href]", self.stop_event,
            ):
                heading = soup.find("h1")
                cards = soup.select(".blog-cat_list > .w-dyn-item > .blogs-featured_card")
                if (heading is None or heading.get_text(" ", strip=True) != "Advanced Persistent Threat (APT)"
                        or not cards):
                    raise DiscoveryError(page_url, ValueError("Sekoia APT collection missing"))
                added = 0
                for card in cards:
                    if self.stop_event.is_set():
                        return
                    link = card.select_one("a.link-item[href]")
                    title = card.select_one("h2")
                    categories = [item.get_text(" ", strip=True) for item in card.select('[fs-list-field="filter"]')]
                    if link is None or title is None or "APT" not in categories:
                        raise DiscoveryError(page_url, ValueError("Sekoia APT card metadata missing"))
                    url = urljoin(page_url, link["href"])
                    target = urlsplit(url)
                    if (target.scheme != "https" or target.hostname != urlsplit(self.source.base_url).hostname
                            or not target.path.startswith("/blog/")):
                        raise DiscoveryError(page_url, ValueError(f"Unexpected Sekoia article URL: {url}"))
                    if url in seen:
                        continue
                    seen.add(url)
                    added += 1
                    date = card.select_one(".blogs-featured_card-cap > .text-size-small")
                    yield Report(url, [{
                        "entry_url": entry_url, "listing_url": page_url,
                        "title": title.get_text(" ", strip=True),
                        "published_at": date.get_text(" ", strip=True) if date else None,
                        "categories": categories, "review_status": "unreviewed",
                    }])
                if not added:
                    raise DiscoveryError(page_url, ValueError("Sekoia returned repeated article results"))
