"""The single article-number authority of an output collection.

Numbers are assigned per identity (source + URL), never recycled, and shared by collection,
PDF derivation and packaging. The registry is `<output_root>/.package/article_ids.json`
(version 1, unchanged format). Every reservation is a short critical section guarded by a
process-wide `flock` on `.package/article_ids.lock` plus an in-process lock: re-read the
persisted registry, look the identity up, otherwise take max + 1, write atomically, and only
then return. Callers never hold this lock across network requests, downloads or PDF work.
"""
import fcntl
import json
import threading
from pathlib import Path

from .storage import FileStorage

REGISTRY = "article_ids.json"
LOCK = "article_ids.lock"
MIGRATION_MARKER = "migration.json"
_THREAD_LOCK = threading.Lock()


def format_id(number: int) -> str:
    return f"{number:06d}"


def numbered_name(article_id: str, extension: str) -> str:
    return f"{article_id}{extension}"


def is_numbered_name(filename: str) -> bool:
    stem = Path(filename).stem
    return stem.isdigit() and len(stem) >= 6


class ArticleIds:
    def __init__(self, output_root, *, require_registry: bool = False):
        self.storage = FileStorage(Path(output_root) / ".package")
        self.path = self.storage.path(REGISTRY)
        if require_registry and not self.path.is_file():
            raise FileNotFoundError(f"Article number registry missing: {self.path}")

    # -- reading -----------------------------------------------------------------------------
    def _read(self) -> dict:
        data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {"version": 1, "articles": []}
        if data.get("version") != 1:
            raise ValueError(f"Unsupported article number registry version in {self.path}")
        ids, used = {}, set()
        for article in data["articles"]:
            key = (article["source"], article["url"])
            number = article["id"]
            if type(number) is not int or number < 1 or key in ids or number in used:
                raise ValueError(f"Duplicate or invalid entry in {self.path}: {article}")
            ids[key] = number
            used.add(number)
        data["_ids"] = ids
        return data

    def lookup(self, source: str, url: str) -> str | None:
        number = self._read()["_ids"].get((source, url))
        return format_id(number) if number else None

    def all(self) -> dict[tuple[str, str], str]:
        return {key: format_id(number) for key, number in self._read()["_ids"].items()}

    def migration_in_progress(self) -> dict | None:
        marker = self.storage.path(MIGRATION_MARKER)
        if not marker.is_file():
            return None
        record = json.loads(marker.read_text(encoding="utf-8"))
        return record if record.get("status") != "completed" else None

    # -- reserving ---------------------------------------------------------------------------
    def reserve(self, source: str, url: str) -> str:
        return self.reserve_many([(source, url)])[source, url]

    def reserve_many(self, identities) -> dict[tuple[str, str], str]:
        """Return numbers for every identity, assigning new ones after the highest reserved."""
        identities = list(dict.fromkeys(identities))
        with _THREAD_LOCK, self.storage.path(LOCK).open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if self.migration_in_progress():
                raise RuntimeError(f"Article numbering migration is unfinished for {self.storage.root.parent}; "
                                   "finish or resume it before collecting or packaging")
            data = self._read()
            ids = data.pop("_ids")
            new = [key for key in identities if key not in ids]
            if new:
                next_id = max(ids.values(), default=0) + 1
                for source, url in new:
                    ids[source, url] = next_id
                    data["articles"].append({"source": source, "url": url, "id": next_id})
                    next_id += 1
                # Persist before returning: a later failure may leave a gap, never a reused number.
                self.storage.write(REGISTRY, (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            return {key: format_id(ids[key]) for key in identities}
