import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlsplit

from .config_loader import CrawlerConfig, PROJECT_ROOT, SourceConfig
from .registry import load_adapter
from .shared.fetchers.http import HTTPFetcher
from .shared.fetchers.document import document_from_response
from .shared.article_ids import ArticleIds, numbered_name
from .shared.collection_lock import collection_lock
from .shared.naming import filename_from_url
from .shared.discovery import collect_reports
from .shared.report_index import export_classifications
from .shared.failures import export_failures, failure_record
from .shared.source_risks import export_source_risks
from .shared.output_notes import export_output_notes
from .shared.state import StateStore
from .shared.run_record import RunRecord
from .shared.storage import source_storage


LOGGER = logging.getLogger(__name__)


class BaseCrawler:
    def __init__(self, config: CrawlerConfig, source_names: list[str] | None = None):
        self.config = config
        self.sources = self._select_sources(source_names or [])
        self.stop_event = threading.Event()

    def _select_sources(self, names: list[str]) -> tuple[SourceConfig, ...]:
        if not names:
            return self.config.sources

        available = {source.name: source for source in self.config.sources}
        missing = [name for name in names if name not in available]
        if missing:
            raise ValueError(f"Sources are not enabled by this profile: {', '.join(missing)}")
        selected = set(names)
        return tuple(source for source in self.config.sources if source.name in selected)

    def stop(self) -> None:
        self.stop_event.set()

    def run(self) -> int:
        adapter_classes = {
            source.name: load_adapter(source.adapter)
            for source in self.sources
        }
        output_root = self._runtime_path("output_root") / self.config.data_namespace
        state_root = self._runtime_path("state_root") / self.config.data_namespace
        groups = {}
        for source in self.sources:
            host = urlsplit(source.base_url).hostname
            if not host:
                raise ValueError(f"Source '{source.name}' base_url must have a hostname")
            groups.setdefault(host.removeprefix("www."), []).append(source)
        # One operation per collection: collecting, migrating, converting and packaging never overlap.
        with collection_lock(output_root, "collect"):
            return self._run_locked(adapter_classes, groups, output_root, state_root)

    def _run_locked(self, adapter_classes, groups, output_root, state_root) -> int:
        self.article_ids = ArticleIds(output_root)
        state = StateStore(
            state_root / "completed.sqlite3",
            track_failures=bool(self.config.failure_file),
        )
        try:
            with RunRecord(self.config, self.sources, output_root, state_root, state.run_id, self.stop_event) as record:
                self.run_record = record
                result = self._run_groups(groups, adapter_classes, output_root, state)
                pdf = self.config.runtime.get("pdf", {})
                if not self.stop_event.is_set() and (pdf.get("enabled") or pdf.get("archive_resources")):
                    from .pdf.pipeline import run_pdf

                    pdf_result = run_pdf(
                        output_root, state_root, pdf, self.config.runtime["http"], self.stop_event,
                        sources={source.name for source in self.sources},
                        fetch_resources=pdf.get("archive_resources", False),
                        archive_only=not pdf.get("enabled", False),
                        adapters={source.name: source.adapter for source in self.sources},
                    )
                    record.data["pdf"] = {"exit_code": pdf_result, "summary_file": str(output_root / "pdf-run.json")}
                    if pdf_result:
                        result = pdf_result
                if self.config.classification_file:
                    export_output_notes(output_root, state_root,
                                        classification_file=self.config.classification_file,
                                        failure_file=self.config.failure_file,
                                        source_risk_file=self.config.source_risk_file)
                return result
        finally:
            state.close()

    def _run_groups(self, groups, adapter_classes, output_root, state) -> int:
        failures = 0
        executor = ThreadPoolExecutor(max_workers=self.config.runtime["concurrency"].get("sites", 1))
        futures = []
        try:
            for sources in groups.values():
                if self.stop_event.is_set():
                    break
                futures.append(executor.submit(self._run_site, sources, adapter_classes, output_root, state))
            for future in as_completed(futures):
                if self.stop_event.is_set():
                    break
                failures += future.result()
        except BaseException:
            # An unexpected scheduler/worker failure must not leave sibling jobs running.
            self.stop()
            raise
        finally:
            if self.stop_event.is_set():
                for future in futures:
                    future.cancel()
            # All source/download workers must finish before exporting or closing SQLite.
            executor.shutdown(wait=True, cancel_futures=True)
            try:
                if self.config.classification_file:
                    export_classifications(state, output_root, self.config.classification_file, self.config.profile)
            finally:
                try:
                    if self.config.failure_file:
                        export_failures(state, output_root, self.config.failure_file, self.config.profile)
                finally:
                    if self.config.source_risk_file:
                        export_source_risks(self.config, self.sources, output_root, state.run_id)

        if self.stop_event.is_set():
            return 130
        return 1 if failures else 0

    def _run_site(self, sources, adapter_classes, output_root, state) -> int:
        failures = 0
        for source in sources:
            if self.stop_event.is_set():
                break
            fetchers = {}
            self.run_record.source_started(source.name)
            try:
                # A source owns its sessions/drivers; closing it cannot affect another site.
                fetchers = self._create_fetchers(source)
                adapter = adapter_classes[source.name](source, fetchers, self.stop_event)
                storage = source_storage(output_root, source.name, source.source_family)
                failures += self._run_source(source, adapter, fetchers, storage, state)
            except InterruptedError:
                self.stop()
            except Exception as error:
                failures += 1
                self._record_failure(state, source, None, "source", error)
            finally:
                for fetcher in fetchers.values():
                    fetcher.close()
                self.run_record.source_finished(source.name)
        return failures

    def _run_source(self, source, adapter, fetchers, storage, state) -> int:
        def discovery_failed(url, error):
            self._record_failure(state, source, url, "discovery", error)

        reports, failures = collect_reports(
            adapter, source, self.stop_event, discovery_failed,
            on_excluded=lambda report, reason: self.run_record.excluded(source, report, reason),
        )
        self.run_record.add(source.name, "discovered", len(reports))
        LOGGER.info("%s discovered %d report URLs (limit: %s)", source.name, len(reports), source.max_reports)
        pending = []
        skipped = 0
        for report in reports:
            if self.stop_event.is_set():
                break
            metadata = report.metadata(source)
            saved = state.get_report(source.name, report.url)
            if saved and storage.exists(saved["filename"]):
                state.mark_completed(source.name, report.url, saved["filename"], metadata)
                skipped += 1
                self.run_record.add(source.name, "skipped")
                LOGGER.info("Skipped completed report: %s %s", source.name, report.url)
                continue
            if saved:
                state.unmark_completed(source.name, report.url)
            pending.append((report.url, metadata))

        concurrency = self.config.runtime["concurrency"]
        workers = (
            concurrency["browser_downloads"]
            if source.content == "browser"
            else concurrency["downloads"]
        )
        downloaded = 0
        executor = ThreadPoolExecutor(max_workers=workers)
        futures = {}

        try:
            for url, metadata in pending:
                if self.stop_event.is_set():
                    break
                future = executor.submit(
                    self._download,
                    source,
                    adapter,
                    url,
                    fetchers,
                    storage,
                    state,
                    metadata,
                )
                futures[future] = url

            for future in as_completed(futures):
                if self.stop_event.is_set():
                    break
                try:
                    future.result()
                except InterruptedError:
                    self.stop()
                    break
                except Exception:
                    pass  # The worker persists and logs the original failure.
        finally:
            if self.stop_event.is_set():
                for future in futures:
                    future.cancel()
            executor.shutdown(wait=True, cancel_futures=True)

        # Include active workers that finished after interruption, without counting cancelled work.
        for future in futures:
            if future.cancelled():
                continue
            try:
                downloaded += bool(future.result())
            except InterruptedError:
                pass
            except Exception:
                failures += 1

        LOGGER.info(
            "%s finished: %d downloaded, %d skipped, %d failed",
            source.name,
            downloaded,
            skipped,
            failures,
        )
        return failures

    def _record_failure(self, state, source, url, stage, error, origins=()):
        self.run_record.add(source.name, "failed")
        LOGGER.error("%s failed: source=%s url=%s", stage, source.name, url,
                     exc_info=(type(error), error, error.__traceback__))
        if self.config.failure_file:
            state.record_failure(failure_record(source.name, url, stage, error, list(origins)))

    def _download(self, source, adapter, url, fetchers, storage, state, metadata) -> bool:
        try:
            return self._save_download(source, adapter, url, fetchers, storage, state, metadata)
        except InterruptedError:
            raise
        except Exception as error:
            self._record_failure(state, source, url, "report", error, metadata["origins"])
            raise

    def _save_download(self, source, adapter, url, fetchers, storage, state, metadata) -> bool:
        if self.stop_event.is_set():
            return False
        # Classified (APT) sources get their permanent article number before any request; a
        # failed download keeps the number and reuses it on retry. CTI mode keeps URL-based names.
        article_id = self.article_ids.reserve(source.name, url) if source.source_family else None
        if fetch_content := getattr(adapter, "fetch_content", None):
            document = fetch_content(url)
        else:
            document = document_from_response(fetchers[source.content].get(url), url)
        metadata = {**metadata, "final_url": document.final_url, "content_type": document.content_type,
                    "download_run_id": state.run_id}
        if article_id:
            metadata["article_id"] = article_id
        preferred = (
            numbered_name(article_id, document.extension)
            if article_id
            else str(Path(filename_from_url(url)).with_suffix(document.extension))
        )
        filename = state.prepare_report(source.name, url, preferred, metadata, storage)
        output_path = storage.write(filename, document.content)
        state.mark_completed(source.name, url, filename, metadata)
        self.run_record.add(source.name, "downloaded")
        LOGGER.info("Saved source=%s url=%s file=%s", source.name, url, output_path)
        return True

    def _runtime_path(self, name: str) -> Path:
        path = Path(self.config.runtime[name])
        return path if path.is_absolute() else PROJECT_ROOT / path

    def _create_fetchers(self, source: SourceConfig) -> dict:
        modes = {source.discovery, source.content}
        fetchers = {}
        if "http" in modes:
            fetchers["http"] = HTTPFetcher(self.config.runtime["http"], self.stop_event)
        if "browser" in modes:
            from .shared.fetchers.browser import BrowserFetcher

            fetchers["browser"] = BrowserFetcher(
                self.config.runtime["browser"],
                self.stop_event,
            )
        return fetchers
