import threading
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit

from bs4 import BeautifulSoup

from ..shared.reports import Report
from ..shared.fetchers.document import document_from_response
from ..config_loader import SourceConfig
from ..shared.navigation.browser import load_more_pages


ITEM_SELECTOR = "div#content-hub-items div.js-item"


class Adapter:
    def __init__(self, source: SourceConfig, fetchers: dict, stop_event: threading.Event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.content_fetcher = fetchers[source.content]
        self.stop_event = stop_event

    def discover(self):
        if self.source.source_family == "activity_reports":
            yield from self._discover_threat_intelligence()
            return
        for html in load_more_pages(
            self.fetcher,
            self.source.start_urls[0],
            ITEM_SELECTOR,
            "#js-show-more",
            self.stop_event,
        ):
            soup = BeautifulSoup(html, "html.parser")
            for item in soup.select(ITEM_SELECTOR):
                heading = item.select_one("h3.c-lb__title")
                link = heading.find("a", href=True) if heading else None
                if link:
                    yield Report(urljoin(self.source.base_url, link["href"]))

    def _discover_threat_intelligence(self):
        for start_url in self.source.start_urls:
            response = self.fetcher.get(start_url)
            soup = BeautifulSoup(response.text, "html.parser")
            hub = soup.select_one("#content-hub-items")
            category = parse_qs(urlsplit(start_url).query).get("category", [""])[0]
            option = next((o for o in soup.select('select[name="Category"] option')
                           if o.get("value") == category), None)
            if (not category or hub is None or hub.get("data-category") != category
                    or option is None or not option.get_text(strip=True).startswith("Threat Intelligence")):
                raise ValueError("NCC directory did not preserve the Threat Intelligence category")
            categories = category.split(",")
            cards = hub.select(".js-item[data-id]")
            if not cards:
                raise ValueError(f"No NCC threat intelligence articles at {response.url}")
            excluded = [card["data-id"] for card in cards]
            for card in cards:
                link = card.select_one("h3 a[href]")
                if link is None:
                    raise ValueError("NCC article card has no report link")
                yield from self._report(start_url, response.url, 1, link["href"], link.get_text(" ", strip=True))
            if soup.select_one("#js-show-more") is None:
                continue
            endpoint = urljoin(response.url, "/api/related/query") + "?" + urlencode({"culture": hub["data-culture"]})
            payload = {
                "ContentTypes": hub["data-contenttypes"].split(","),
                "ResourceTypes": hub.get("data-resource", "").split(",") if hub.get("data-resource") else [],
                "Categories": categories, "Sectors": [], "Services": [],
                "SortOrder": hub.get("data-sortorder") or None, "RootNode": hub["data-rootnode"],
                "Authors": [], "ExcludedIds": excluded,
                "ResultAmount": hub["data-totalresults"], "IsUserQuery": True,
                "CultureFallback": hub.get("data-fallback") == "true",
            }
            page = 2
            while not self.stop_event.is_set():
                response = self.fetcher.post(endpoint, json=payload)
                data = response.json()
                items, more = data["content"], data["moreResultsAvailable"]
                if not isinstance(items, list) or not isinstance(more, bool):
                    raise ValueError("NCC directory has invalid pagination data")
                ids = [str(item["id"]) for item in items]
                if (items and not set(ids) - set(excluded)) or (not items and more):
                    raise ValueError("NCC threat intelligence pagination did not advance")
                excluded.extend(i for i in ids if i not in excluded)
                for item in items:
                    item_categories = {str(c["id"]) for c in item["tags"]["categories"]}
                    if not item_categories.intersection(categories):
                        raise ValueError(f"NCC returned an article outside Threat Intelligence: {item['url']}")
                    yield from self._report(start_url, response.url, page, item["url"], item["title"])
                if not more:
                    break
                page += 1

    def _report(self, entry_url, listing_url, page, path, title):
        url = urljoin(entry_url, path)
        parsed = urlsplit(url)
        if parsed.netloc != urlsplit(entry_url).netloc or not parsed.path.startswith("/research/"):
            raise ValueError(f"NCC returned a link outside research articles: {url}")
        origin = {
            "entry_url": entry_url, "listing_url": listing_url, "listing_page": page,
            "topic": "Threat Intelligence", "title": title,
            "selection_basis": "publisher_threat_intelligence_category",
        }
        yield Report(url, [origin])

    def fetch_content(self, url):
        response = self.content_fetcher.get(url)
        if self.source.source_family == "activity_reports":
            soup = BeautifulSoup(response.content, "html.parser")
            # NCC sometimes publishes the report as a PDF-only WordPress file block.
            # Header/footer policy PDFs are unrelated and must not be followed.
            targets = set()
            for node in soup.select('main .wp-block-file object[type="application/pdf"][data], main .wp-block-file a[download][href]'):
                target = urljoin(response.url, node.get("data") or node["href"])
                if urlsplit(target).path.lower().endswith(".pdf"):
                    targets.add(target)
            if len(targets) > 1:
                raise ValueError(f"NCC article contains multiple report PDFs; selection needs review: {url}")
            if targets:
                target = targets.pop()
                return document_from_response(self.content_fetcher.get(target), target)
        return document_from_response(response, url)
