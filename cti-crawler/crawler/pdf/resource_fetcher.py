"""Host-limited image requests, including redirects and shared server backoff."""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import logging
import threading
import time
from urllib.parse import urlsplit

import requests

from ..shared.fetchers.http import HTTPFetcher

LOGGER = logging.getLogger(__name__)


@dataclass
class HostState:
    active: int = 0
    next_start: float = 0
    cooldown: float = 0
    failures: int = 0


class HostLimits:
    def __init__(self, stop_event, parallel=2, interval=1.0):
        self.stop = stop_event
        self.parallel = parallel
        self.interval = interval
        self.condition = threading.Condition()
        self.hosts = {}

    @contextmanager
    def request(self, url):
        host = urlsplit(url).hostname
        with self.condition:
            state = self.hosts.setdefault(host, HostState())
            while True:
                if self.stop.is_set():
                    raise InterruptedError("PDF resource preparation is stopping")
                delay = max(state.next_start, state.cooldown) - time.monotonic()
                if state.active < self.parallel and delay <= 0:
                    state.active += 1
                    state.next_start = time.monotonic() + self.interval
                    break
                self.condition.wait(min(max(delay, 0.05), 0.25))
        try:
            yield
        finally:
            with self.condition:
                state.active -= 1
                self.condition.notify_all()

    def response(self, response):
        host = urlsplit(response.url).hostname
        with self.condition:
            state = self.hosts.setdefault(host, HostState())
            if response.status_code not in {429, 503}:
                if response.status_code < 400:
                    state.failures = 0
                return
            state.failures += 1
            delay = min(30 * state.failures, 120)
            value = response.headers.get('Retry-After', '').strip()
            if value.isdigit():
                delay = max(delay, int(value))
            elif value:
                try:
                    until = parsedate_to_datetime(value)
                    if until.tzinfo is None:
                        until = until.replace(tzinfo=timezone.utc)
                    delay = max(delay, (until - datetime.now(timezone.utc)).total_seconds())
                except (ValueError, TypeError, OverflowError):
                    pass
            state.cooldown = max(state.cooldown, time.monotonic() + delay)
            self.condition.notify_all()
        LOGGER.warning("PDF resource host %s paused for %.0fs after HTTP %d",
                       host, delay, response.status_code)


class ResourceFetcher(HTTPFetcher):
    def __init__(self, settings, stop_event, *, parallel=2, interval=1.0):
        super().__init__(settings, stop_event)
        self.limits = HostLimits(stop_event, parallel, interval)

    def _send(self, method, url, **kwargs):
        # ResourceCache only sends GET with optional headers. Retain Requests'
        # cookie/auth redirect handling, but acquire the actual host at every hop.
        session = self._session()
        prepared = session.prepare_request(requests.Request(method, url, **kwargs))
        history = []
        while True:
            environment = session.merge_environment_settings(prepared.url, {}, False, None, None)
            with self.limits.request(prepared.url):
                response = session.send(prepared, timeout=self.timeout,
                                        allow_redirects=False, **environment)
                self.limits.response(response)
            if response.next is None:
                response.history = history
                return response
            history.append(response)
            if len(history) > session.max_redirects:
                raise requests.TooManyRedirects("Too many image redirects", response=response)
            prepared = response.next
            response.close()
