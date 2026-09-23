import logging
import threading
from collections.abc import Callable, Iterable, Iterator

import requests

from ..discovery import DiscoveryError
from ..reports import Report


LOGGER = logging.getLogger(__name__)


def path_page_url(start_url: str, page_number: int) -> str:
    return f"{start_url.rstrip('/')}/page/{page_number}/"


def numbered_pages(
    fetcher,
    start_url: str,
    extract_urls: Callable[[str], Iterable[str]],
    stop_event: threading.Event,
    page_url: Callable[[str, int], str] = path_page_url,
    empty_page_tolerance: int = 0,
    page_delay: float = 0.0,
) -> Iterator[Report]:
    """Walk numbered pages until one yields nothing new. `empty_page_tolerance` allows that many
    consecutive pages without any article link before stopping (some sites serve an empty page
    in the middle of a listing); the walk still ends at the first page whose links are all known."""
    seen: set[str] = set()
    page_number = 1
    empty_pages = 0
    first_request = True

    while not stop_event.is_set():
        current_url = start_url if page_number == 1 else page_url(start_url, page_number)
        # Some listings rate-limit a fast walk (ESET answered 429 around page 45); pace the pages.
        if page_delay and not first_request and stop_event.wait(page_delay):
            break
        first_request = False
        try:
            response = fetcher.get(current_url)
            urls = list(extract_urls(response.text))
        except requests.RequestException as error:
            if page_number == 1 or not empty_page_tolerance:
                raise DiscoveryError(current_url, error) from error
            # A single broken page in the middle of a listing (ESET's page 45 answers 429 to every
            # client) is treated like an empty page so the walk can continue; it is logged, not hidden.
            LOGGER.warning("Listing page %s failed (%s); treated as an empty page", current_url, error)
            urls = []
        if not urls:
            if page_number == 1:
                raise ValueError(f"No article links found at {current_url}")
            empty_pages += 1
            if empty_pages > empty_page_tolerance:
                break
            page_number += 1
            continue
        empty_pages = 0

        new_urls = []
        for url in urls:
            if url not in seen:
                seen.add(url)
                new_urls.append(url)
        if not new_urls:
            break

        for url in new_urls:
            yield Report(url, [{"entry_url": start_url, "listing_url": response.url}])
        page_number += 1
