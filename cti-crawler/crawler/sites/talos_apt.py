from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from ..shared.discovery import DiscoveryError
from ..shared.reports import Report


class Adapter:
    """Use Talos' public Ghost index; its HTML next links repeat the same list."""

    def __init__(self, source, fetchers, stop_event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.stop_event = stop_event

    def discover(self):
        for entry_url in self.source.start_urls:
            location = entry_url
            try:
                if self.stop_event.is_set():
                    return
                response = self.fetcher.get(entry_url)
                soup = BeautifulSoup(response.text, "html.parser")
                settings = soup.select_one("script[data-sodo-search][data-key]")
                if settings is None:
                    raise ValueError("Talos public Content API settings missing")
                endpoint = settings["data-sodo-search"].rstrip("/") + "/ghost/api/content/posts/"
                if urlsplit(endpoint).hostname != "cisco-talos-blog.ghost.io" or urlsplit(endpoint).scheme != "https":
                    raise ValueError("Unexpected Talos Content API host")
                location = endpoint
                page = 1
                seen_pages, seen_urls = set(), set()
                while page is not None and not self.stop_event.is_set():
                    if page in seen_pages:
                        raise ValueError("Talos Content API repeated a page")
                    seen_pages.add(page)
                    payload = self.fetcher.get(endpoint, params={
                        "key": settings["data-key"], "filter": "tag:apt",
                        "limit": 100, "include": "tags",
                        "fields": "id,title,url,published_at", "page": page,
                    }).json()
                    pagination = payload["meta"]["pagination"]
                    posts = payload["posts"]
                    if pagination["page"] != page:
                        raise ValueError("Talos Content API returned the wrong page")
                    if not posts and pagination["total"]:
                        raise ValueError("Talos Content API returned an incomplete list")
                    added = 0
                    for post in posts:
                        if self.stop_event.is_set():
                            return
                        tags = [tag["slug"] for tag in post["tags"]]
                        if "apt" not in tags:
                            raise ValueError("Talos Content API returned a post outside the APT category")
                        url = post["url"]
                        if urlsplit(url).hostname != urlsplit(self.source.base_url).hostname:
                            raise ValueError("Talos Content API returned an unexpected article host")
                        if url in seen_urls:
                            continue
                        seen_urls.add(url)
                        added += 1
                        yield Report(url, [{
                            "entry_url": entry_url, "listing_url": endpoint,
                            "listing_page": page, "title": post["title"],
                            "published_at": post["published_at"], "tags": tags,
                        }])
                    if posts and not added:
                        raise ValueError("Talos Content API repeated article results")
                    page = pagination["next"]
            except InterruptedError:
                raise
            except Exception as error:
                raise DiscoveryError(location, error) from error
