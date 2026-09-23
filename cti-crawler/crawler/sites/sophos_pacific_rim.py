from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
from requests.utils import default_user_agent

from ..shared.discovery import DiscoveryError
from ..shared.fetchers.document import document_from_response
from ..shared.reports import Report


SECTION_TITLE = "Sophos X-Ops research on Pacific Rim"


class Adapter:
    """Collect the publisher's research section of the Pacific Rim dossier."""

    def __init__(self, source, fetchers, stop_event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.content_fetcher = fetchers[source.content]
        self.stop_event = stop_event

    @staticmethod
    def request_headers():
        # The site times out with the shared Chrome impersonation header, while
        # the ordinary requests identity is accepted. Keep this site-local.
        return {"User-Agent": default_user_agent()}

    def fetch_content(self, url):
        response = self.content_fetcher.get(url, headers=self.request_headers())
        return document_from_response(response, url)

    def discover(self):
        for entry_url in self.source.start_urls:
            if self.stop_event.is_set():
                return
            page_url = entry_url
            try:
                response = self.fetcher.get(entry_url, headers=self.request_headers())
                page_url = response.url
                # The HTTP response streams this section outside the initial main.
                # Parse the whole document; no browser or guessed pagination needed.
                soup = BeautifulSoup(response.text, "html.parser")
                section = soup.select_one("section#sophosxops")
                heading = section.find(["h2", "h3"]) if section else None
                if heading is None or heading.get_text(" ", strip=True) != SECTION_TITLE:
                    raise ValueError(f"Pacific Rim research section missing at {page_url}")
                links = section.select("a[href]")
                if not links:
                    raise ValueError(f"No Pacific Rim research articles at {page_url}")
                for link in links:
                    if self.stop_event.is_set():
                        return
                    url = urljoin(page_url, link["href"])
                    target = urlsplit(url)
                    if (target.scheme != "https" or target.hostname != urlsplit(self.source.base_url).hostname
                            or not target.path.startswith("/en-us/blog/")):
                        raise ValueError(f"Unexpected Pacific Rim research link: {url}")
                    title = link.select_one("p.title-6")
                    yield Report(url, [{
                        "entry_url": entry_url,
                        "listing_url": page_url,
                        "series": "Pacific Rim",
                        "section": SECTION_TITLE,
                        "title": (title or link).get_text(" ", strip=True),
                    }])
            except InterruptedError:
                raise
            except Exception as error:
                raise DiscoveryError(page_url, error) from error
