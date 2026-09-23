"""Where an original document's derived PDF lives.

Numbered originals (`000123.html`) share their number with the derived PDF (`000123.pdf`).
Legacy long-name originals, including the unchanged CTI mode, keep `<name>.pdf` next to the
original (`report.html` -> `report.html.pdf`). Every module that pairs an HTML original with
its PDF must use this rule instead of building the name itself.
"""
from pathlib import Path, PurePosixPath

from .article_ids import is_numbered_name


def derived_pdf_name(original_name: str) -> str:
    if is_numbered_name(original_name):
        return f"{Path(original_name).stem}.pdf"
    return f"{original_name}.pdf"


def derived_pdf_path(original: Path) -> Path:
    return original.with_name(derived_pdf_name(original.name))


def derived_pdf_relative(relative: str) -> str:
    path = PurePosixPath(relative)
    return (path.parent / derived_pdf_name(path.name)).as_posix()
