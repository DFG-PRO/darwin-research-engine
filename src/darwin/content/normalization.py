"""Deterministic HTML and text normalization."""

from __future__ import annotations

from html.parser import HTMLParser


class ReadableTextHTMLParser(HTMLParser):
    """Small parser that extracts readable text while skipping script/style markup."""

    block_tags = {
        "article",
        "blockquote",
        "br",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "p",
        "pre",
        "section",
        "table",
        "td",
        "th",
        "tr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in {"script", "style", "noscript"}:
            self.skip_depth += 1
            return
        if self.skip_depth == 0 and normalized_tag in self.block_tags:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if normalized_tag in {"script", "style", "noscript"} and self.skip_depth > 0:
            self.skip_depth -= 1
            return
        if self.skip_depth == 0 and normalized_tag in self.block_tags:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth == 0:
            self.parts.append(data)

    def text(self) -> str:
        return normalize_plain_text("".join(self.parts))


def normalize_content(raw_body: bytes, content_type: str | None) -> str:
    """Normalize supported text content without paraphrasing."""

    text = raw_body.decode("utf-8", errors="replace")
    if _is_html(content_type):
        parser = ReadableTextHTMLParser()
        parser.feed(text)
        parser.close()
        return parser.text()
    return normalize_plain_text(text)


def normalize_plain_text(text: str) -> str:
    """Normalize newlines and whitespace deterministically."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [" ".join(line.strip().split()) for line in normalized.split("\n")]

    paragraphs: list[str] = []
    current: list[str] = []
    for line in lines:
        if line:
            current.append(line)
        elif current:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))

    return "\n\n".join(paragraphs).strip()


def _is_html(content_type: str | None) -> bool:
    return content_type is not None and "html" in content_type.lower()
