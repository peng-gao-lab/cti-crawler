"""One operation at a time per output collection.

Collecting, migrating article names, standalone PDF conversion and packaging all hold this
non-blocking `flock` on `<output_root>/.package/collection.lock` for their whole duration, so
a second instance is refused immediately instead of racing on files, the number registry or
the state database. The PDF stage keeps its own `.pdf/lock`; the fixed order is collection
lock first, PDF lock second, and the PDF stage never takes the collection lock itself.
Different output collections do not affect each other.
"""
import fcntl
from contextlib import contextmanager
from pathlib import Path


class CollectionBusy(RuntimeError):
    pass


@contextmanager
def collection_lock(output_root, operation: str):
    root = Path(output_root) / ".package"
    root.mkdir(parents=True, exist_ok=True)
    with (root / "collection.lock").open("a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            handle.seek(0)
            holder = handle.read().strip() or "another operation"
            raise CollectionBusy(f"{output_root} is busy ({holder}); refusing to start {operation}") from error
        handle.seek(0)
        handle.truncate()
        handle.write(operation)
        handle.flush()
        try:
            yield
        finally:
            handle.seek(0)
            handle.truncate()
            fcntl.flock(handle, fcntl.LOCK_UN)
