import threading
from urllib.parse import parse_qs, urljoin, urlsplit

from bs4 import BeautifulSoup

from ..shared.reports import Report
from ..config_loader import SourceConfig
from ..shared.navigation.browser import clicked_pages


CARD_SELECTOR = "div.blog_post_filter_module_teaserCard__a_4Yd"
RESEARCH_QUERY = """
query page($offset: Int, $tag: String) {
  blogsGraphql(limit:12, offset:$offset, tag:$tag, order:"-") {
    count
    entities { nid title path { alias } fieldBlogMainCategory { entity { name } } }
  }
}
"""


class Adapter:
    def __init__(self, source: SourceConfig, fetchers: dict, stop_event: threading.Event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.stop_event = stop_event

    def discover(self):
        if self.source.source_family == "activity_reports":
            yield from self._discover_research()
            return
        seen = set()
        pages = clicked_pages(
            self.fetcher,
            self.source.start_urls[0],
            CARD_SELECTOR,
            "li.rc-pagination-next",
            self.stop_event,
        )
        for html in pages:
            soup = BeautifulSoup(html, "html.parser")
            for card in soup.select(CARD_SELECTOR):
                link = card.find("a", href=True)
                if not link:
                    continue
                url = urljoin(self.source.base_url, link["href"])
                if url not in seen:
                    seen.add(url)
                    yield Report(url)

    def _discover_research(self):
        for start_url in self.source.start_urls:
            category = parse_qs(urlsplit(start_url).query).get("tag", [""])[0]
            if category != "Security Research":
                raise ValueError("Zscaler activity source requires the Security Research category")
            endpoint = urljoin(start_url, "/api/graphql")
            offset = 0
            seen_ids = set()
            while not self.stop_event.is_set():
                response = self.fetcher.post(endpoint, json={
                    "query": RESEARCH_QUERY, "variables": {"offset": offset, "tag": category},
                })
                data = response.json()
                if data.get("errors"):
                    raise ValueError(f"Zscaler directory query failed: {data['errors']}")
                index = data["data"]["blogsGraphql"]
                items, total = index["entities"], int(index["count"])
                if not isinstance(items, list) or (not items and offset < total):
                    raise ValueError("Zscaler research index has no article list")
                ids = {item["nid"] for item in items}
                if items and not ids - seen_ids:
                    raise ValueError("Zscaler research pagination did not advance")
                seen_ids.update(ids)
                for item in items:
                    path = item["path"]["alias"]
                    actual_category = item["fieldBlogMainCategory"]["entity"]["name"]
                    if actual_category != category or not path.startswith("/blogs/security-research/"):
                        raise ValueError(f"Zscaler returned an article outside the research category: {path}")
                    url = urljoin(self.source.base_url, path)
                    origin = {
                        "entry_url": start_url, "listing_url": response.url,
                        "index_offset": offset, "topic": category, "title": item["title"],
                        "selection_basis": "publisher_security_research_category",
                    }
                    yield Report(url, [origin])
                offset += len(items)
                if offset >= total:
                    break
