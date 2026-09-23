"""Shared reading of frozen collection manifests.

A collection manifest is a local JSON list of report files in one third-party archive, pinned to
one repository commit so every download URL is reproducible. Discovery makes no requests; the
shared HTTP fetcher downloads the files. Each source module keeps its own repository identity and
its own rule for which entries it accepts, so one source can never serve another's list.
"""
import json
from pathlib import Path

from ..shared.reports import Report


def load(source, collection: str) -> dict:
    """Read the manifest of `source` and check it belongs to `collection` and pins a commit."""
    if source.manifest is None:
        raise ValueError(f"Source '{source.name}' needs a manifest path")
    manifest = json.loads(Path(source.manifest).read_text(encoding="utf-8"))
    if manifest.get("collection") != collection or not manifest.get("commit"):
        raise ValueError(f"Manifest {source.manifest} is not a pinned {collection} list")
    return manifest


def reports(source, manifest: dict, collection: str, stop_event, accepts):
    """Yield one Report per manifest item; `accepts(item)` decides what this source may serve.

    Origins record where the file comes from (collection, commit, repository path), why it was
    selected and, when the preparation step had evidence for them, the original publisher and URL.
    The collection is an aggregator, never the publisher of the report.
    """
    entry_url = source.start_urls[0]
    for item in manifest["items"]:
        if stop_event.is_set():
            return
        if not accepts(item) or not item["path"].lower().endswith(".pdf"):
            # The runtime list only carries selected report PDFs; anything else is a preparation error.
            raise ValueError(f"Manifest item is not a selected report PDF: {item.get('path')}")
        origin = {
            "entry_url": entry_url,
            "collection": collection,
            "collection_commit": manifest["commit"],
            "collection_path": item["path"],
            "selection": item["selection"],
            "selection_basis": manifest.get("selection", ""),
        }
        for key in ("report_folder", "publisher_hint", "original_url", "original_file_name"):
            if item.get(key):
                origin[key] = item[key]
        yield Report(item["url"], [origin])
