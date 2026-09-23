import json
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..shared.reports import Report
from ..shared.naming import normalize_report_url


class Adapter:
    """Follow Unit 42's explicit APT tag and its public load-more requests."""

    @staticmethod
    def pdf_content_selectors(url):
        return ("main .section--article", "main .blog-editor > .l-container")

    def __init__(self, source, fetchers, stop_event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.stop_event = stop_event

    def discover(self):
        seen = set()
        for entry_url in self.source.start_urls:
            if self.stop_event.is_set():
                return
            response = self.fetcher.get(entry_url)
            soup = BeautifulSoup(response.text, "html.parser")
            marker = "var blog_loadmore_params ="
            script = next((s.get_text() for s in soup.find_all("script")
                           if marker in s.get_text()), None)
            element = soup.select_one("[data-load-posts]")
            if script is None or element is None:
                raise ValueError(f"Unit 42 listing parameters missing at {entry_url}")
            params = json.JSONDecoder().raw_decode(script.split(marker, 1)[1].lstrip())[0]
            query = json.loads(params["posts"])
            if query.get("tag") != "advanced-persistent-threat":
                raise ValueError("Unit 42 source did not resolve to the Advanced Persistent Threat tag")
            for page in range(1, int(params["max_page"]) + 1):
                if self.stop_event.is_set():
                    return
                data = {
                    "action": "loadmore", "query": params["posts"],
                    "page": max(1, page - 1), "loadstatus": "init" if page == 1 else "more",
                    "nonce": params["nonce"], "tracking_prefix": element["data-tracking"],
                    "language": element["data-lang"], "sort_by": "",
                }
                listing = self.fetcher.post(params["ajaxurl"], data=data,
                                            headers={"Referer": entry_url})
                payload = listing.json()
                if payload.get("ajax_results") is False:
                    break
                cards = BeautifulSoup(payload["html"], "html.parser").select(".l-card .card-content")
                if not cards:
                    raise ValueError(f"Unit 42 returned no report cards on page {page}")
                new_urls = 0
                for card in cards:
                    heading = card.select_one("h5.post-title")
                    link = heading.find_parent("a", href=True) if heading else None
                    if link is None:
                        raise ValueError("Unit 42 report card has no title link")
                    url = normalize_report_url(urljoin(entry_url, link["href"]))
                    category = card.select_one(".card-category")
                    origin = {
                        "entry_url": entry_url, "listing_url": listing.url, "listing_page": page,
                        "topic": "Advanced Persistent Threat", "title": heading.get_text(" ", strip=True),
                        "category": category.get_text(" ", strip=True) if category else "",
                        "tags": [a.get_text(" ", strip=True) for a in card.select(".card-tags a")],
                    }
                    if url not in seen:
                        seen.add(url)
                        new_urls += 1
                    yield Report(url, [origin])
                if not new_urls:
                    break
