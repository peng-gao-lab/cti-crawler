import logging
import threading

import requests


LOGGER = logging.getLogger(__name__)


class HTTPFetcher:
    def __init__(self, settings: dict, stop_event: threading.Event):
        self.timeout = settings["timeout_seconds"]
        self.retries = settings["retries"]
        self.user_agent = settings.get("user_agent")
        self.stop_event = stop_event
        self._local = threading.local()
        self._sessions: list[requests.Session] = []
        self._lock = threading.Lock()

    def _session(self) -> requests.Session:
        if not hasattr(self._local, "session"):
            session = requests.Session()
            if self.user_agent:
                session.headers["User-Agent"] = self.user_agent
            self._local.session = session
            with self._lock:
                self._sessions.append(session)
        return self._local.session

    def get(self, url: str, **kwargs) -> requests.Response:
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        return self._request("POST", url, **kwargs)

    def _send(self, method: str, url: str, **kwargs) -> requests.Response:
        return self._session().request(method, url, timeout=self.timeout, **kwargs)

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        for attempt in range(self.retries + 1):
            if self.stop_event.is_set():
                raise InterruptedError("Crawler is stopping")

            try:
                response = self._send(method, url, **kwargs)
                response.raise_for_status()
                return response
            except requests.RequestException as error:
                status = error.response.status_code if error.response is not None else None
                retryable = status is None or status in {408, 429} or status >= 500
                if not retryable or attempt == self.retries:
                    raise
                delay = min(2**attempt, 5)
                if status == 429:
                    # Rate limited: honour Retry-After when given, otherwise back off for real.
                    retry_after = error.response.headers.get("Retry-After", "")
                    delay = int(retry_after) if retry_after.isdigit() else 30 * (attempt + 1)
                LOGGER.warning("HTTP %s %s attempt %d/%d failed (%s); retrying in %ss",
                               method, url, attempt + 1, self.retries + 1, error, delay,
                               extra={"request_error": error})
                if self.stop_event.wait(delay):
                    raise InterruptedError("Crawler is stopping")

        raise RuntimeError("Unreachable retry state")

    def close(self) -> None:
        with self._lock:
            sessions = self._sessions
            self._sessions = []
        for session in sessions:
            session.close()
