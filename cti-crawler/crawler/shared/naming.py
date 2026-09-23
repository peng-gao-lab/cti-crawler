import re
from urllib.parse import unquote, urlsplit, urlunsplit


def filename_from_url(url: str) -> str:
    parts = [
        re.sub(r"[^A-Za-z0-9._-]+", "_", unquote(part)).strip("_")
        for part in urlsplit(url).path.split("/")
        if part
    ]
    return f"{'__'.join(parts) or 'index'}.html"


def normalize_report_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


def report_filename_from_url(url: str, extension: str) -> str:
    """Readable cross-domain name; StateStore reserves collision suffixes."""
    parts = urlsplit(url)
    path = re.sub(r"\.(?:html?|pdf)$", "", parts.path, flags=re.IGNORECASE)
    label = f"{parts.netloc}__{path}"
    if parts.query:
        label += f"__{parts.query}"
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", unquote(label)).strip("._")
    return f"{stem[:180] or 'report'}{extension}"
