"""Deterministic source content segmentation."""

from __future__ import annotations

from dataclasses import dataclass

from darwin.content.hashing import sha256_text


@dataclass(frozen=True)
class ContentSegment:
    """Addressable normalized text segment."""

    segment_identifier: str
    segment_order: int
    text: str
    locator: str
    char_start: int
    char_end: int
    line_start: int
    line_end: int
    fingerprint: str


def segment_text(normalized_text: str, *, base_locator: str | None) -> list[ContentSegment]:
    """Split normalized text into deterministic paragraph segments."""

    segments: list[ContentSegment] = []
    cursor = 0
    for index, paragraph in enumerate(normalized_text.split("\n\n"), start=1):
        text = paragraph.strip()
        if not text:
            cursor += len(paragraph) + 2
            continue

        char_start = normalized_text.find(text, cursor)
        if char_start < 0:
            char_start = cursor
        char_end = char_start + len(text)
        line_start = normalized_text.count("\n", 0, char_start) + 1
        line_end = normalized_text.count("\n", 0, char_end) + 1
        identifier = f"segment-{len(segments) + 1:04d}"
        locator = f"{base_locator or ''}#segment-{len(segments) + 1}"
        segments.append(
            ContentSegment(
                segment_identifier=identifier,
                segment_order=len(segments) + 1,
                text=text,
                locator=locator,
                char_start=char_start,
                char_end=char_end,
                line_start=line_start,
                line_end=line_end,
                fingerprint=sha256_text(text),
            )
        )
        cursor = char_end

    return segments
