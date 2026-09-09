import re
import sqlite3
from dataclasses import dataclass

from app.database.sqlite_db import get_connection


PROVENANCE_CONTEXT_VERSION = "provenance-context-v1"
DEFAULT_CONTEXT_RADIUS = 800

MENTION_KEY_PATTERN = re.compile(
    r"^p(?P<page>\d+):(?P<start>\d+):(?P<end>\d+)$"
)


@dataclass(frozen=True)
class MentionLocation:
    page_number: int
    start: int
    end: int


def parse_mention_key(
    mention_key: str,
) -> MentionLocation:
    """
    Parse the stable numeric mention key:

        p{page_number}:{start}:{end}

    The start/end offsets refer to the original page text
    used by Numeric Scanner v2.
    """

    match = MENTION_KEY_PATTERN.fullmatch(
        mention_key
    )

    if match is None:
        raise ValueError(
            f"Invalid mention_key: {mention_key!r}"
        )

    page_number = int(
        match.group("page")
    )
    start = int(
        match.group("start")
    )
    end = int(
        match.group("end")
    )

    if start < 0:
        raise ValueError(
            "mention start must be >= 0"
        )

    if end <= start:
        raise ValueError(
            "mention end must be greater than start"
        )

    return MentionLocation(
        page_number=page_number,
        start=start,
        end=end,
    )


def _load_document_pages(
    document_id: str,
) -> list[dict]:
    """
    Load page text for one document in deterministic order.

    This is intentionally separate from Numeric Scanner.
    Provenance enrichment can rebuild richer context without
    rescanning numeric mentions.
    """

    connection = get_connection()
    connection.row_factory = sqlite3.Row

    try:
        rows = connection.execute(
            """
            SELECT
                page_number,
                text

            FROM pages

            WHERE document_id = ?

            ORDER BY page_number
            """,
            (
                document_id,
            ),
        ).fetchall()

        return [
            {
                "page_number":
                    int(row["page_number"]),

                "text":
                    row["text"] or "",
            }
            for row in rows
        ]

    finally:
        connection.close()


def _take_left_context(
    *,
    pages: list[dict],
    page_index: int,
    start: int,
    radius: int,
) -> str:
    remaining = radius
    pieces: list[str] = []

    current_text = pages[
        page_index
    ]["text"]

    current_piece = current_text[
        max(
            0,
            start - remaining,
        ):
        start
    ]

    if current_piece:
        pieces.append(
            current_piece
        )

        remaining -= len(
            current_piece
        )

    previous_index = (
        page_index - 1
    )

    while (
        remaining > 0
        and
        previous_index >= 0
    ):
        previous_page = pages[
            previous_index
        ]

        previous_text = (
            previous_page["text"]
        )

        piece = previous_text[
            max(
                0,
                len(previous_text)
                - remaining,
            ):
        ]

        if piece:
            pieces.append(
                (
                    f"\n[PAGE "
                    f"{previous_page['page_number']}]\n"
                    f"{piece}"
                )
            )

            remaining -= len(
                piece
            )

        previous_index -= 1

    pieces.reverse()

    return "".join(
        pieces
    )


def _take_right_context(
    *,
    pages: list[dict],
    page_index: int,
    end: int,
    radius: int,
) -> str:
    remaining = radius
    pieces: list[str] = []

    current_text = pages[
        page_index
    ]["text"]

    current_piece = current_text[
        end:
        min(
            len(current_text),
            end + remaining,
        )
    ]

    if current_piece:
        pieces.append(
            current_piece
        )

        remaining -= len(
            current_piece
        )

    next_index = (
        page_index + 1
    )

    while (
        remaining > 0
        and
        next_index < len(pages)
    ):
        next_page = pages[
            next_index
        ]

        next_text = (
            next_page["text"]
        )

        piece = next_text[
            :
            min(
                len(next_text),
                remaining,
            )
        ]

        if piece:
            pieces.append(
                (
                    f"\n[PAGE "
                    f"{next_page['page_number']}]\n"
                    f"{piece}"
                )
            )

            remaining -= len(
                piece
            )

        next_index += 1

    return "".join(
        pieces
    )


def build_provenance_context(
    *,
    document_id: str,
    page_number: int,
    mention_key: str,
    raw_text: str,
    radius: int = DEFAULT_CONTEXT_RADIUS,
) -> str:
    """
    Rebuild a provenance-oriented context window from pages.

    The window is character-bounded on each side of the target
    and can cross page boundaries.

    Numeric Scanner v2 remains unchanged. The stable mention
    key is used to recover the exact target location.

    The target is explicitly marked so the semantic classifier
    does not accidentally reason about another nearby number.
    """

    if radius <= 0:
        raise ValueError(
            "radius must be greater than 0"
        )

    location = parse_mention_key(
        mention_key
    )

    if (
        location.page_number
        != page_number
    ):
        raise ValueError(
            "mention_key page number does not match "
            "the row page_number"
        )

    pages = _load_document_pages(
        document_id
    )

    if not pages:
        raise ValueError(
            f"No pages found for document {document_id!r}"
        )

    page_index = None

    for index, page in enumerate(
        pages
    ):
        if (
            page["page_number"]
            == page_number
        ):
            page_index = index
            break

    if page_index is None:
        raise ValueError(
            "Target page is missing from pages table: "
            f"document={document_id!r}, "
            f"page={page_number}"
        )

    current_text = pages[
        page_index
    ]["text"]

    if (
        location.end
        > len(current_text)
    ):
        raise ValueError(
            "mention offsets exceed current page text length"
        )

    target_text = current_text[
        location.start:
        location.end
    ]

    if (
        target_text
        != raw_text
    ):
        raise ValueError(
            "mention_key no longer points to raw_text; "
            "page text and numeric mention cache are inconsistent: "
            f"expected={raw_text!r}, "
            f"actual={target_text!r}"
        )

    left_context = (
        _take_left_context(
            pages=pages,
            page_index=page_index,
            start=location.start,
            radius=radius,
        )
    )

    right_context = (
        _take_right_context(
            pages=pages,
            page_index=page_index,
            end=location.end,
            radius=radius,
        )
    )

    return (
        f"{left_context}"
        f"[TARGET_START]"
        f"{target_text}"
        f"[TARGET_END]"
        f"{right_context}"
    )
