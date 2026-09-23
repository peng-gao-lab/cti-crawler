"""One discovery contract: Report values, recoverable failures, or interruption."""
from dataclasses import dataclass
import logging

from .reports import merge_report
from .naming import normalize_report_url


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class DiscoveryFailure:
    url: str | None
    error: Exception


class DiscoveryError(Exception):
    def __init__(self, url, error):
        super().__init__(str(error))
        self.url = url
        self.error = error


def collect_reports(adapter, source, stop_event, on_failure, on_excluded=None):
    reports = {}
    failures = 0
    excluded = set()

    def failed(url, error):
        nonlocal failures
        failures += 1
        on_failure(url, error)

    discovery = iter(adapter.discover())
    try:
        while not stop_event.is_set():
            try:
                item = next(discovery)
            except StopIteration:
                break
            if isinstance(item, DiscoveryFailure):
                failed(item.url, item.error)
                continue
            key = normalize_report_url(item.url)
            if reason := source.excluded_urls.get(key):
                if key not in excluded:
                    excluded.add(key)
                    LOGGER.info("Excluded reviewed URL: source=%s url=%s reason=%s", source.name, item.url, reason)
                    if on_excluded:
                        on_excluded(item, reason)
                continue
            merge_report(reports, item)
            if source.max_reports is not None and len(reports) >= source.max_reports:
                break
    except InterruptedError:
        raise
    except DiscoveryError as error:
        failed(error.url, error.error)
    except Exception as error:
        response = getattr(error, "response", None)
        request = getattr(error, "request", None)
        failed(getattr(request, "url", None) or getattr(response, "url", None), error)
    finally:
        close = getattr(discovery, "close", None)
        if close:
            close()
    return list(reports.values()), failures
