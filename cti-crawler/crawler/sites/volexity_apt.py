from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from ..shared.discovery import DiscoveryError
from ..shared.reports import Report


class Adapter:
    """Collect the reviewed whole-blog scope, without a date or category filter."""

    def __init__(self, source, fetchers, stop_event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.stop_event = stop_event

    def discover(self):
        endpoint = urljoin(self.source.base_url, "/wp-json/wp/v2/posts")
        try:
            page, pages = 1, 1
            seen = set()
            while page <= pages and not self.stop_event.is_set():
                response = self.fetcher.get(endpoint, params={
                    "per_page": 100, "page": page, "orderby": "date", "order": "desc",
                    "_fields": "id,date,link,title,categories,tags",
                })
                posts = response.json()
                pages = int(response.headers["X-WP-TotalPages"])
                total = int(response.headers["X-WP-Total"])
                if not isinstance(posts, list) or (not posts and total):
                    raise ValueError("Volexity returned an invalid or incomplete post index")
                added = 0
                for post in posts:
                    if self.stop_event.is_set():
                        return
                    url = post["link"]
                    target = urlsplit(url)
                    if (target.scheme != "https" or target.hostname != urlsplit(self.source.base_url).hostname
                            or not target.path.startswith("/blog/")):
                        raise ValueError(f"Unexpected Volexity article URL: {url}")
                    if url in seen:
                        continue
                    seen.add(url)
                    added += 1
                    yield Report(url, [{
                        "entry_url": self.source.start_urls[0], "listing_url": endpoint,
                        "listing_page": page, "published_at": post["date"],
                        "title": BeautifulSoup(post["title"]["rendered"], "html.parser").get_text(" ", strip=True),
                        "categories": post.get("categories", []), "tags": post.get("tags", []),
                        "review_status": "unreviewed", "scope": "whole_blog",
                    }])
                if posts and not added:
                    raise ValueError("Volexity returned repeated post results")
                page += 1
        except InterruptedError:
            raise
        except Exception as error:
            raise DiscoveryError(endpoint, error) from error
