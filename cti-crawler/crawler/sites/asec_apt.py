import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from ..shared.discovery import DiscoveryError
from ..shared.reports import Report


APT_CATEGORY = 195196
MONTH = r"(?:January|February|March|April|May|June|July|August|September|October|November|December|Dec\.)"
PERIOD = rf"(?:{MONTH} \d{{4}}|\d{{4}} {MONTH})"
# Publisher series names, including historical titles; not a generic Trend filter.
MONTHLY_SERIES = re.compile(
    rf"(?:(?:ATIP_)?{PERIOD}[\s_–-]+)?"
    r"Threat Trend Report on (?:APT Groups|APT Attacks(?: \(South Korea\))?|Kimsuky Group)"
    r"(?: [–-] .+)?"
    rf"|{PERIOD} (?:"
    r"(?:Major )?APT Group Trends(?: Report)?(?: \(South Korea\))?"
    r"|APT Attack Trends? Report \((?:South Korea|Domestic)\)"
    r"|Major Issues on APT Attacks in South Korea)"
    rf"|APT Group Trends in {PERIOD}",
    re.IGNORECASE,
)


def is_monthly_digest(title):
    return MONTHLY_SERIES.fullmatch(" ".join(title.split())) is not None


class Adapter:
    """Collect the English APT category, excluding approved monthly series."""

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
                    "categories": APT_CATEGORY, "per_page": 100, "page": page,
                    "orderby": "date", "order": "desc",
                    "_fields": "id,date,link,title,categories",
                })
                posts = response.json()
                pages = int(response.headers["X-WP-TotalPages"])
                total = int(response.headers["X-WP-Total"])
                if not isinstance(posts, list) or (not posts and total):
                    raise ValueError("ASEC returned an invalid or incomplete post index")
                added = 0
                for post in posts:
                    if self.stop_event.is_set():
                        return
                    if APT_CATEGORY not in post["categories"]:
                        raise ValueError("ASEC returned a post outside the English APT category")
                    url = post["link"]
                    target = urlsplit(url)
                    if (target.scheme != "https" or target.hostname != urlsplit(self.source.base_url).hostname
                            or not re.fullmatch(r"/en/\d+/", target.path)):
                        raise ValueError(f"Unexpected ASEC article URL: {url}")
                    if url in seen:
                        continue
                    seen.add(url)
                    added += 1
                    title = BeautifulSoup(post["title"]["rendered"], "html.parser").get_text(" ", strip=True)
                    if is_monthly_digest(title):
                        continue
                    yield Report(url, [{
                        "entry_url": self.source.start_urls[0], "listing_url": endpoint,
                        "listing_page": page, "published_at": post["date"],
                        "title": title, "categories": post["categories"],
                        "review_status": "unreviewed",
                    }])
                # Count before filtering: an all-digest page must not end traversal.
                if posts and not added:
                    raise ValueError("ASEC returned repeated post results")
                page += 1
        except InterruptedError:
            raise
        except Exception as error:
            raise DiscoveryError(endpoint, error) from error
