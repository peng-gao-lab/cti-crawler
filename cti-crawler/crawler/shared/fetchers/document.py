from dataclasses import dataclass
from urllib.parse import urlsplit

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class FetchedDocument:
    content: bytes
    extension: str
    final_url: str
    content_type: str


class DocumentError(ValueError):
    def __init__(self, message, response, *, reason="unknown"):
        super().__init__(message)
        self.response = response
        self.reason = reason


def document_from_response(response, requested_url: str) -> FetchedDocument:
    content = response.content
    media_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    original = urlsplit(requested_url)
    final = urlsplit(response.url)
    if original.path.strip("/") and not final.path.strip("/"):
        raise DocumentError(f"Report redirected to a homepage: {response.url}", response, reason="homepage_redirect")
    if not content.strip():
        raise DocumentError(f"Empty report: {requested_url}", response, reason="empty_content")

    if content[:1024].lstrip().startswith(b"%PDF-"):
        extension = ".pdf"
    else:
        if media_type == "application/pdf" or original.path.lower().endswith(".pdf"):
            raise DocumentError(f"PDF report returned non-PDF content: {requested_url}", response, reason="invalid_pdf")
        soup = BeautifulSoup(content, "html.parser")
        if media_type not in {"text/html", "application/xhtml+xml"} and soup.find("html") is None:
            raise DocumentError(f"Unsupported report format: {media_type or 'unknown'}", response, reason="unsupported_format")
        title = soup.title.get_text(" ", strip=True).lower() if soup.title else ""
        blocked_titles = (
            "just a moment", "access denied", "attention required", "page not found",
            "404 not found", "verify you are human", "checking your browser",
        )
        if any(marker in title for marker in blocked_titles) or title in {"sign in", "log in", "login"}:
            raise DocumentError(f"Report returned an error, login or challenge page: {response.url}", response, reason="unavailable_page")
        if soup.select_one("#challenge-form, #cf-challenge-running"):
            raise DocumentError(f"Report returned a browser challenge: {response.url}", response, reason="unavailable_page")
        extension = ".html"
    return FetchedDocument(content, extension, response.url, media_type)
