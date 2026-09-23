from ..discovery import DiscoveryError

from urllib.parse import urljoin

from bs4 import BeautifulSoup


def linked_pages(fetcher, start_url, next_selector, stop_event):
    """Read HTTP lists by following their actual next-page links."""
    url = start_url
    seen = set()
    while url and url not in seen and not stop_event.is_set():
        seen.add(url)
        try:
            response = fetcher.get(url)
        except InterruptedError:
            raise
        except Exception as error:
            raise DiscoveryError(url, error) from error
        soup = BeautifulSoup(response.text, "html.parser")
        yield response.url, soup
        link = soup.select_one(next_selector)
        url = urljoin(response.url, link["href"]) if link else None
