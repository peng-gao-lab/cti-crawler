import threading
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from ..shared.reports import Report
from ..config_loader import SourceConfig


class Adapter:
    def __init__(self, source: SourceConfig, fetchers: dict, stop_event: threading.Event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.stop_event = stop_event

    def discover(self):
        if self.source.source_family == "activity_reports":
            yield from self._discover_reports()
            return
        response = self.fetcher.get(self.source.start_urls[0])
        data = response.json().get("data", [])
        if not isinstance(data, list):
            raise ValueError("Recorded Future index has no data list")

        for page in data:
            path = page.get("path")
            if isinstance(path, str) and path.startswith("/blog/"):
                yield Report(urljoin(self.source.base_url, path))

    def _discover_reports(self):
        for start_url in self.source.start_urls:
            page_url = start_url
            expected_offset = int(dict(parse_qsl(urlsplit(start_url).query)).get("offset", 0))
            while not self.stop_event.is_set():
                response = self.fetcher.get(page_url)
                index = response.json()
                data = index.get("data")
                if not isinstance(data, list):
                    raise ValueError(f"Recorded Future index has no data list: {page_url}")
                offset, total = int(index["offset"]), int(index["total"])
                if offset != expected_offset or (not data and offset < total):
                    raise ValueError(f"Recorded Future index did not advance: {page_url}")
                for item in data:
                    path = item.get("path")
                    # Index resource types distinguish articles from landing pages.
                    if (
                        not isinstance(path, str)
                        or not path.startswith(("/blog/", "/research/"))
                        or item.get("resourceType") not in {"blog", "research"}
                    ):
                        continue
                    url = urljoin(self.source.base_url, path)
                    origin = {
                        "entry_url": start_url, "listing_url": response.url,
                        "index_offset": offset, "topic": "Recorded Future reports",
                        "title": item.get("title", ""),
                    }
                    yield Report(url, [origin])
                expected_offset = offset + len(data)
                if expected_offset >= total:
                    break
                parts = urlsplit(start_url)
                query = dict(parse_qsl(parts.query))
                query["offset"] = str(expected_offset)
                page_url = urlunsplit(parts._replace(query=urlencode(query)))
