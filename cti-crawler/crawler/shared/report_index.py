import json
import sqlite3
from pathlib import Path

from .storage import FileStorage, source_directory
from .reports import merge_metadata


# APT means Advanced Persistent Threat, independent of the actor's name.
REPORT_CLASSES = ("explicit_apt", "multistep_attack")


def saved_reports(state_dir, output_dir, sources=None, adapters=None):
    """Read completed originals, including sources disabled in the current profile."""
    database = Path(state_dir) / "completed.sqlite3"
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as db:
        rows = db.execute("SELECT c.source,c.url,c.filename,r.metadata FROM completed c "
                          "JOIN reports r ON c.source=r.source AND c.url=r.url AND c.filename=r.filename").fetchall()
    for source, url, filename, raw in rows:
        if sources is not None and source not in sources:
            continue
        metadata = json.loads(raw)
        family = next((o.get("source_family") for o in metadata.get("origins", []) if o.get("source") == source), None)
        relative = source_directory(source, family) / filename
        if not (output_dir / relative).is_file():
            relative = Path(source) / filename
        yield {"source": source, "url": url, "base_url": metadata.get("final_url") or url,
               "adapter": metadata.get("adapter") or (adapters or {}).get(source),
               "file": relative.as_posix(), "source_family": family}


def export_classifications(state, output_root: Path, filename: str, profile: str) -> None:
    articles = {}
    for source, url, saved_name, metadata in state.completed_reports():
        family = next((origin.get("source_family") for origin in metadata.get("origins", [])
                       if origin.get("source") == source), None)
        relative = source_directory(source, family) / saved_name
        # Sources not selected in this run may still use the previous layout.
        if not (output_root / relative).is_file():
            relative = Path(source) / saved_name
        if not (output_root / relative).is_file():
            continue
        article = articles.setdefault(url, {"url": url, "files": [], "file_run_ids": {}})
        merged = merge_metadata(article, metadata)
        download_run_id = merged.pop("download_run_id", None)
        if download_run_id is not None:
            merged["file_run_ids"][relative.as_posix()] = download_run_id
        if relative.as_posix() not in merged["files"]:
            merged["files"].append(relative.as_posix())
        articles[url] = merged
    for article in articles.values():
        article["files"].sort()
    payload = {"profile": profile, "articles": [articles[url] for url in sorted(articles)]}
    FileStorage(output_root).write(
        filename, (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
