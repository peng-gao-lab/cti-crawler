"""Independent, resumable PDF stage; never changes crawler completion records."""
import fcntl
import json
from collections import deque
import logging
import multiprocessing
import sqlite3
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, wait, FIRST_COMPLETED
from concurrent.futures.process import BrokenProcessPool
from datetime import datetime, timezone
from pathlib import Path

from .archive import ResourceCache, fingerprint, write_json
from .cleanup import current_pdf, release_article, release_shared_cache
from .render import convert, initialize_worker
from .resource_fetcher import ResourceFetcher
from .prepare import prepare
from ..shared.report_index import saved_reports


LOGGER = logging.getLogger(__name__)


def run_pdf(output_dir, state_dir, settings, http_settings, stop_event, *, sources=None,
            fetch_resources=False, archive_only=False, adapters=None):
    output_dir, state_dir = Path(output_dir).resolve(), Path(state_dir).resolve()
    # Read-only lookup also ensures a typo cannot silently create a new crawl database.
    reports = list(saved_reports(state_dir, output_dir, sources, adapters))
    work_dir = output_dir / ".pdf"
    work_dir.mkdir(exist_ok=True)
    with (work_dir / "lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError(f"Another PDF job is already using {output_dir}") from error
        return _run(reports, output_dir, state_dir, work_dir, settings, http_settings, stop_event,
                    fetch_resources, archive_only)


def _run(reports, output_dir, state_dir, work_dir, settings, http_settings, stop_event, fetch_resources, archive_only):
    run_id = datetime.now(timezone.utc).isoformat()
    run = {"run_id": run_id, "status": "running", "fetch_resources": fetch_resources,
           "archive_only": archive_only, "workers": settings["workers"],
           "resource_workers": settings.get("resource_workers", 1),
           "resource_host_concurrency": settings.get("resource_host_concurrency", 2),
           "resource_host_interval_seconds": settings.get("resource_host_interval_seconds", 1.0),
           "counts": {"converted": 0, "archived": 0, "skipped": 0, "native_pdf": 0, "failed": 0},
           "records": [],
           "cleanup": {"enabled": settings.get("cleanup_after_success", True) and not archive_only,
                       "files_removed": 0, "temporary_bytes_removed": 0,
                       "resources_removed": 0, "cache_bytes_reclaimed": 0, "errors": []}}
    write_json(output_dir / "pdf-run.json", run)
    fetcher = ResourceFetcher(
        http_settings, stop_event, parallel=settings.get("resource_host_concurrency", 2),
        interval=settings.get("resource_host_interval_seconds", 1.0)) if fetch_resources else None
    cache = ResourceCache(work_dir / "resources.sqlite3", fetcher)
    executor = None
    pending = {}
    preparing = {}
    ready = deque()
    preparation = None

    def record(path, entry, outcome, error=None):
        entry["updated_at"] = datetime.now(timezone.utc).isoformat()
        entry["run_id"] = run_id
        if error is not None:
            entry["error"] = {"type": type(error).__name__, "message": str(error)}
            LOGGER.warning("PDF stage failed: %s: %s", entry["file"], error,
                           exc_info=(type(error), error, error.__traceback__))
        else:
            entry.pop("error", None)
            LOGGER.info("PDF %s: %s", outcome, entry["file"])
        write_json(path, entry)
        if (run["cleanup"]["enabled"] and outcome in {"converted", "skipped"}
                and current_pdf(entry, output_dir)):
            try:
                removed = release_article(path.parent)
                for key, value in removed.items():
                    run["cleanup"][key] += value
                entry["archive_status"] = "cleaned"
                entry.pop("archive_revision", None)
                entry.pop("cleanup_error", None)
            except OSError as cleanup_error:
                entry["cleanup_error"] = str(cleanup_error)
                run["cleanup"]["errors"].append({"file": entry["file"], "error": str(cleanup_error)})
                LOGGER.warning("PDF working file cleanup failed: %s", entry["file"], exc_info=True)
            write_json(path, entry)
        run["counts"][outcome] += 1
        run["records"].append({"file": entry["file"], "status": outcome, "error": entry.get("error")})
        with (output_dir / "pdf-events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
        write_json(output_dir / "pdf-run.json", run)

    def harvest(future):
        path, entry = pending.pop(future)
        try:
            entry["checks"] = future.result()
            if fingerprint(output_dir / entry["file"]) != entry["input_revision"]:
                raise ValueError("HTML changed during conversion; rerun PDF stage")
            entry["pdf_revision"] = fingerprint(output_dir / entry["pdf"])
            entry["conversion_status"] = "converted"
            record(path, entry, "converted")
        except BrokenProcessPool:
            raise  # A dead worker pool is not a document-specific failure.
        except Exception as error:
            entry["conversion_status"] = "failed"
            record(path, entry, "failed", error)

    try:
        resource_workers = settings.get("resource_workers", 1)
        preparation = ThreadPoolExecutor(max_workers=resource_workers)
        if not archive_only:
            executor = ProcessPoolExecutor(max_workers=settings["workers"],
                                           initializer=initialize_worker,
                                           mp_context=multiprocessing.get_context("spawn"))
        remaining = iter(reports)
        exhausted = False
        # Bound ready archives and memory as well as running CPU work.
        capacity = resource_workers + (0 if archive_only else settings["workers"])
        while True:
            if stop_event.is_set():
                for future in preparing:
                    future.cancel()
                ready.clear()  # Prepared files are retained for resumption.
            else:
                while ready and len(pending) < settings["workers"]:
                    item = ready.popleft()
                    entry = item.entry
                    entry["conversion_status"] = "running"
                    write_json(item.path, entry)
                    future = executor.submit(convert, str(item.path.parent / "print.html"),
                                             str(output_dir / entry["pdf"]))
                    pending[future] = (item.path, entry)
                while (not exhausted and len(preparing) < resource_workers
                       and len(preparing) + len(ready) + len(pending) < capacity):
                    report = next(remaining, None)
                    if report is None:
                        exhausted = True
                        break
                    future = preparation.submit(prepare, report, output_dir, work_dir,
                                                cache, archive_only, stop_event)
                    preparing[future] = report
            active = set(preparing) | set(pending)
            if not active:
                if ready and not stop_event.is_set():
                    continue
                break
            done, _ = wait(active, timeout=0.5, return_when=FIRST_COMPLETED)
            # Completed renders are recorded even while image requests are waiting.
            for future in done & pending.keys():
                harvest(future)
            for future in done & preparing.keys():
                preparing.pop(future)
                if future.cancelled():
                    continue
                item = future.result()
                if item.outcome == "native_pdf":
                    run["counts"]["native_pdf"] += 1
                elif item.outcome == "ignored":
                    continue
                elif item.outcome == "interrupted":
                    stop_event.set()
                elif item.outcome == "ready":
                    if not stop_event.is_set():
                        ready.append(item)
                else:
                    record(item.path, item.entry, item.outcome, item.error)
        if run["cleanup"]["enabled"] and not stop_event.is_set():
            try:
                run["cleanup"].update(release_shared_cache(
                    cache, saved_reports(state_dir, output_dir), output_dir, work_dir))
            except (OSError, ValueError, sqlite3.Error) as error:
                run["cleanup"]["errors"].append({"file": "resources.sqlite3", "error": str(error)})
                LOGGER.warning("PDF shared cache cleanup failed", exc_info=True)
            LOGGER.info("PDF cleanup: %s", run["cleanup"])
        code = 130 if stop_event.is_set() else (1 if run["counts"]["failed"] or run["cleanup"]["errors"] else 0)
        run["status"] = "interrupted" if code == 130 else ("failed" if code else "completed")
        run["exit_code"] = code
        return code
    except BaseException:
        stop_event.set()
        run["status"] = "failed"
        run["exit_code"] = 1
        raise
    finally:
        if preparation:
            preparation.shutdown(wait=True, cancel_futures=True)
        if executor:
            executor.shutdown(wait=True, cancel_futures=True)
        if fetcher:
            fetcher.close()
        cache.close()
        run["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_json(output_dir / "pdf-run.json", run)
