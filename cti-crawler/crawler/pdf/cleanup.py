"""Reclaim derived working files without touching reports or pending local archives."""
import json

from .archive import fingerprint


def current_pdf(entry, output_dir):
    if entry.get("conversion_status") != "converted":
        return False
    original = output_dir / entry["file"]
    pdf = output_dir / entry["pdf"]
    return (original.is_file() and pdf.is_file()
            and entry.get("input_revision") == fingerprint(original)
            and entry.get("pdf_revision") == fingerprint(pdf))


def release_article(directory):
    removed = size = 0
    # Explicit generated filenames only; retain status, source HTML and final PDF.
    for name in ("print.html", "print.html.part", "previous.pdf"):
        path = directory / name
        if path.is_file():
            size += path.stat().st_size
            path.unlink()
            removed += 1
    return {"files_removed": removed, "temporary_bytes_removed": size}


def release_shared_cache(cache, reports, output_dir, work_dir):
    # Inspect the whole collection, including sources omitted from this invocation.
    for report in reports:
        original = output_dir / report["file"]
        if original.suffix.lower() not in {".html", ".htm"}:
            continue
        directory = work_dir / report["file"]
        status = directory / "status.json"
        entry = json.loads(status.read_text()) if status.is_file() else {}
        if current_pdf(entry, output_dir):
            continue
        archive = directory / "print.html"
        # A ready print.html embeds every image; even a failed render can retry
        # from it without the shared cache. Partial/missing/legacy archives pin
        # the cache because their remaining resource dependencies are unknown.
        if (original.is_file() and entry.get("input_revision") == fingerprint(original)
                and entry.get("archive_status") == "ready" and archive.is_file()
                and entry.get("archive_revision") == fingerprint(archive)):
            continue
        return {"cache_deferred_for": report["file"]}
    return cache.clear()
