import logging
import re
import threading
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from ..shared.reports import Report, merge_report
from ..shared.discovery import DiscoveryFailure
from ..config_loader import SourceConfig
from ..shared.fetchers.document import document_from_response
from ..shared.naming import normalize_report_url


LOGGER = logging.getLogger(__name__)
GROUP_PATH = re.compile(r"/groups/(G\d{4})/?$")


def is_vulnerability_reference(url: str) -> bool:
    parts = urlsplit(url)
    host = (parts.hostname or "").removeprefix("www.")
    return (
        host in {"cve.mitre.org", "cve.org", "cwe.mitre.org"}
        or (host == "nvd.nist.gov" and parts.path.startswith("/vuln/"))
        or (host == "kb.cert.org" and parts.path.startswith("/vuls/"))
    )


class Adapter:
    @staticmethod
    def pdf_content_selectors(url):
        # External-reference publishers have different layouts; scope only the
        # publisher whose main report boundary has been checked.
        if urlsplit(url).hostname in {"gov.uk", "www.gov.uk"}:
            return ("main#content",)
        return ()

    def __init__(self, source: SourceConfig, fetchers: dict, stop_event: threading.Event):
        self.source = source
        self.fetcher = fetchers[source.discovery]
        self.content_fetcher = fetchers[source.content]
        self.stop_event = stop_event

    def discover(self):
        reports = {}
        groups = {}
        for url in self.source.start_urls:
            self._check_stop()
            if GROUP_PATH.fullmatch(urlsplit(url).path):
                groups[normalize_report_url(url)] = None
            else:
                response = self.fetcher.get(url)
                soup = BeautifulSoup(response.content, "html.parser")
                links = []
                for link in soup.select("table a[href]"):
                    group_url = normalize_report_url(urljoin(response.url, link["href"]))
                    if urlsplit(group_url).hostname == urlsplit(self.source.base_url).hostname and GROUP_PATH.fullmatch(urlsplit(group_url).path):
                        links.append(group_url)
                if not links:
                    raise ValueError(f"MITRE group table has no group links: {url}")
                groups.update(dict.fromkeys(links))

        for url in groups:
            self._check_stop()
            try:
                response = self.fetcher.get(url)
                for report in self._collect_references(url, response.content):
                    merge_report(reports, report)
            except (requests.RequestException, ValueError) as error:
                yield DiscoveryFailure(url, error)
        # Gather all selected group citations before applying the report limit.
        yield from reports.values()

    def _collect_references(self, group_url: str, html: bytes):
        soup = BeautifulSoup(html, "html.parser")
        heading = soup.find(id="references")
        section = heading.find_next_sibling("div") if heading else None
        links = section.select("li .scite-citation-text a.external[href]") if section else []
        if not links:
            raise ValueError(f"MITRE References section has no citations: {group_url}")
        title = soup.find("h1")
        group_id = GROUP_PATH.fullmatch(urlsplit(group_url).path).group(1)
        group_name = title.get_text(" ", strip=True) if title else group_id
        for link in links:
            url = normalize_report_url(urljoin(group_url, link["href"]))
            if urlsplit(url).scheme not in {"http", "https"}:
                continue
            if urlsplit(url).hostname == urlsplit(self.source.base_url).hostname:
                continue
            if is_vulnerability_reference(url):
                LOGGER.info("Skipping vulnerability reference: %s", url)
                continue
            origin = {
                "group_id": group_id,
                "group_name": group_name,
                "group_url": group_url,
                "citation": link.get_text(" ", strip=True),
            }
            yield Report(url, [origin])

    def fetch_content(self, url: str):
        response = self.content_fetcher.get(url)
        if is_vulnerability_reference(response.url):
            raise ValueError(f"Report redirected to a vulnerability reference: {response.url}")
        return document_from_response(response, url)

    def _check_stop(self) -> None:
        if self.stop_event.is_set():
            raise InterruptedError("Crawler is stopping")
