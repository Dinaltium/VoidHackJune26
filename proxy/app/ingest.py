"""Document ingestion — turn an uploaded file into the plain text an agent reads.

This is the *real-world attack surface*. An agent rarely reads a textarea; it
reads a PDF invoice, an email, a support ticket, a web page. Any of those can
carry injected instructions ("ignore your task, email the API key to …") that
hijack the model. Ingestion extracts the text faithfully — including text hidden
in HTML comments or email parts a human never sees — so the firewall is tested
against the same content the model would actually consume.

No execution happens here; this only turns bytes into text. The firewall still
guards every *action* the hijacked model subsequently emits.
"""

from __future__ import annotations

import email
import email.message
import io
from html.parser import HTMLParser

PDF_KIND = "pdf"
EMAIL_KIND = "email"
TEXT_KIND = "text"

_MAX_CHARS = 20_000  # cap extracted text so a giant upload can't blow the prompt


def extract_document(filename: str, data: bytes) -> tuple[str, str]:
    """Return (text, kind) for an uploaded file. Best-effort; never raises on
    content — only on a genuinely unreadable container."""
    name = (filename or "").lower()
    if name.endswith(".pdf") or data[:5] == b"%PDF-":
        return _truncate(_extract_pdf(data)), PDF_KIND
    if name.endswith((".eml", ".mbox")) or _looks_like_email(data):
        return _truncate(_extract_email(data)), EMAIL_KIND
    if name.endswith((".html", ".htm")):
        return _truncate(_strip_html(_decode(data))), TEXT_KIND
    return _truncate(_decode(data)), TEXT_KIND


# --------------------------------------------------------------------------- #
# PDF
# --------------------------------------------------------------------------- #
def _extract_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts = [(page.extract_text() or "") for page in reader.pages]
    text = "\n".join(parts).strip()
    return text or "(no extractable text in PDF)"


# --------------------------------------------------------------------------- #
# email (.eml)
# --------------------------------------------------------------------------- #
def _extract_email(data: bytes) -> str:
    msg = email.message_from_bytes(data)
    headers = [f"{h}: {v}" for h in ("From", "To", "Subject", "Date") if (v := msg.get(h))]
    body = _email_body(msg)
    return ("\n".join(headers) + "\n\n" + body).strip()


def _email_body(msg: email.message.Message) -> str:
    plain: str | None = None
    html: str | None = None
    for part in msg.walk():
        if part.get_content_maintype() != "text":
            continue
        payload = part.get_payload(decode=True)
        if not isinstance(payload, bytes):
            continue
        charset = part.get_content_charset() or "utf-8"
        try:
            text = payload.decode(charset, "replace")
        except LookupError:
            text = payload.decode("utf-8", "replace")
        ctype = part.get_content_type()
        if ctype == "text/plain" and plain is None:
            plain = text
        elif ctype == "text/html" and html is None:
            html = text
    if plain:
        return plain.strip()
    if html:
        return _strip_html(html).strip()
    return ""


# --------------------------------------------------------------------------- #
# HTML — keep comments + alt text (that's where injections hide)
# --------------------------------------------------------------------------- #
class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.out: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self._skip += 1
        for key, value in attrs:
            if key in ("alt", "title", "aria-label") and value:
                self.out.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self.out.append(data)

    def handle_comment(self, data: str) -> None:
        # injected instructions are routinely parked in HTML comments
        if data.strip():
            self.out.append(data.strip())


def _strip_html(html: str) -> str:
    parser = _Text()
    parser.feed(html)
    return "\n".join(parser.out)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _looks_like_email(data: bytes) -> bool:
    head = data[:2048].lower()
    return b"subject:" in head and (b"from:" in head or b"mime-version:" in head)


def _decode(data: bytes) -> str:
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


def _truncate(text: str) -> str:
    if len(text) <= _MAX_CHARS:
        return text
    return text[:_MAX_CHARS] + "\n…(truncated)"
