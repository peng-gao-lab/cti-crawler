import threading
from collections.abc import Iterator

from ..discovery import DiscoveryError


def load_more_pages(
    fetcher,
    start_url: str,
    item_selector: str,
    button_selector: str,
    stop_event: threading.Event,
    button_text: str | None = None,
) -> Iterator[str]:
    """Yield each visible listing before requesting more items."""
    fetcher.get(start_url, wait_for=item_selector)
    for step in range(fetcher.max_navigation_steps):
        if stop_event.is_set():
            return
        yield fetcher.current_html()
        if stop_event.is_set() or not fetcher.can_click(button_selector, button_text):
            return
        if step + 1 >= fetcher.max_navigation_steps:
            raise DiscoveryError(start_url, ValueError("Load More navigation limit reached"))
        previous_count = fetcher.element_count(item_selector)
        if not fetcher.click(button_selector, text_contains=button_text):
            raise DiscoveryError(start_url, TimeoutError("Load More button could not be clicked"))
        if not fetcher.wait_for_more(item_selector, previous_count):
            raise DiscoveryError(start_url, TimeoutError("Load More did not add content"))


def clicked_pages(
    fetcher,
    start_url: str,
    item_selector: str,
    next_selector: str,
    stop_event: threading.Event,
    disabled_attribute: str = "aria-disabled",
    disabled_value: str = "true",
) -> Iterator[str]:
    fetcher.get(start_url, wait_for=item_selector)
    for step in range(fetcher.max_navigation_steps):
        if stop_event.is_set():
            return
        yield fetcher.current_html()
        if stop_event.is_set() or fetcher.element_count(next_selector) == 0:
            return
        if fetcher.element_attribute(next_selector, disabled_attribute) == disabled_value:
            return
        if step + 1 >= fetcher.max_navigation_steps:
            raise DiscoveryError(start_url, ValueError("Next-page navigation limit reached"))
        previous_item = fetcher.element_attribute(item_selector, "outerHTML")
        if not fetcher.click(next_selector):
            raise DiscoveryError(start_url, TimeoutError("Next-page button could not be clicked"))
        if not fetcher.wait_for_change(item_selector, previous_item):
            raise DiscoveryError(start_url, TimeoutError("Next page did not change content"))
