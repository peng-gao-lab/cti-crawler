"""One article's archive preparation; shared run records stay in the coordinator."""
from dataclasses import dataclass
import json
import logging
from pathlib import Path

from .archive import fingerprint, prepare_html, write_json
from .cleanup import current_pdf
from ..registry import load_adapter
from ..shared.document_paths import derived_pdf_path
from ..shared.storage import FileStorage

LOGGER = logging.getLogger(__name__)


@dataclass
class Prepared:
    path: Path
    entry: dict
    outcome: str
    error: Exception | None = None


def prepare(report, output_dir, work_dir, cache, archive_only, stop_event):
    original = output_dir / report['file']
    directory = work_dir / report['file']
    status_path = directory / 'status.json'
    entry = dict(report)
    if stop_event.is_set():
        # A queued task has not read its prior status yet; leave it untouched.
        return Prepared(status_path, entry, 'interrupted')
    try:
        if original.suffix.lower() == '.pdf':
            if not original.is_file():
                raise FileNotFoundError(f'Original PDF is missing: {original}')
            return Prepared(status_path, entry, 'native_pdf')
        if original.suffix.lower() not in {'.html', '.htm'}:
            return Prepared(status_path, entry, 'ignored')
        directory.mkdir(parents=True, exist_ok=True)
        entry = json.loads(status_path.read_text()) if status_path.exists() else {}
        entry.update(report)
        archive = directory / 'print.html'
        pdf = derived_pdf_path(original)
        entry['pdf'] = pdf.relative_to(output_dir).as_posix()
        adapter = load_adapter(report['adapter']) if report.get('adapter') else None
        boundary = getattr(adapter, 'pdf_content_selectors', None)
        headers = getattr(adapter, 'request_headers', None)
        resources = cache.with_headers(headers() if headers else {})
        selectors = boundary(report['base_url']) if boundary else ()
        revision = fingerprint(original)
        current = (entry.get('input_revision') == revision
                   and entry.get('content_selectors', []) == list(selectors))
        if archive_only and current and entry.get('archive_status') == 'ready' and archive.is_file():
            return Prepared(status_path, entry, 'skipped')
        if current and current_pdf(entry, output_dir):
            return Prepared(status_path, entry, 'skipped')
        entry.pop('checks', None)
        entry.pop('pdf_revision', None)
        if pdf.is_file() and (not current or not archive_only):
            pdf.replace(directory / 'previous.pdf')
        if not current or entry.get('archive_status') != 'ready' or not archive.is_file():
            entry.update(input_revision=revision, archive_status='pending', conversion_status='pending')
            write_json(status_path, entry)
            LOGGER.info('PDF preparing: %s', report['file'])
            html, details = prepare_html(original.read_bytes(), report['base_url'], resources, selectors)
            FileStorage(directory).write('print.html', html.encode('utf-8'))
            entry.update(archive_status='ready', archive_revision=fingerprint(archive), **details)
        entry['conversion_status'] = 'pending'
        write_json(status_path, entry)
        return Prepared(status_path, entry, 'archived' if archive_only else 'ready')
    except InterruptedError as error:
        entry['archive_status'] = 'interrupted'
        write_json(status_path, entry)
        return Prepared(status_path, entry, 'interrupted', error)
    except Exception as error:
        if entry.get('archive_status') != 'ready':
            entry['archive_status'] = 'failed'
        entry['conversion_status'] = 'failed'
        return Prepared(status_path, entry, 'failed', error)
