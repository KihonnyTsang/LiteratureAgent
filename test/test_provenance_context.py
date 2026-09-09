import sqlite3

import pytest

from app.database import sqlite_db
from app.enrichment import provenance_context
from app.enrichment.provenance_context import (
    MentionLocation,
    build_provenance_context,
    parse_mention_key,
)


def install_test_database(
    *,
    tmp_path,
    monkeypatch,
):
    database_path = (
        tmp_path
        / "provenance-context-test.db"
    )

    def get_test_connection():
        connection = sqlite3.connect(
            database_path
        )

        return connection

    monkeypatch.setattr(
        sqlite_db,
        "get_connection",
        get_test_connection,
    )

    monkeypatch.setattr(
        provenance_context,
        "get_connection",
        get_test_connection,
    )

    connection = get_test_connection()

    try:
        connection.execute(
            """
            CREATE TABLE pages (
                document_id TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                text TEXT NOT NULL,
                PRIMARY KEY (
                    document_id,
                    page_number
                )
            )
            """
        )

        connection.executemany(
            """
            INSERT INTO pages (
                document_id,
                page_number,
                text
            )
            VALUES (?, ?, ?)
            """,
            [
                (
                    "doc-1",
                    1,
                    "Previous attribution: "
                    "Smith et al. reported this result. "
                    "END-PAGE-ONE",
                ),
                (
                    "doc-1",
                    2,
                    "TARGET 32 V followed by more discussion.",
                ),
                (
                    "doc-1",
                    3,
                    "NEXT-PAGE-THREE",
                ),
            ],
        )

        connection.commit()

    finally:
        connection.close()


def test_parse_mention_key():
    location = parse_mention_key(
        "p12:4623:4627"
    )

    assert location == MentionLocation(
        page_number=12,
        start=4623,
        end=4627,
    )


def test_invalid_mention_key_is_rejected():
    with pytest.raises(
        ValueError
    ):
        parse_mention_key(
            "page12:1:5"
        )


def test_context_can_cross_previous_page(
    tmp_path,
    monkeypatch,
):
    install_test_database(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )

    context = build_provenance_context(
        document_id="doc-1",
        page_number=2,
        mention_key="p2:7:11",
        raw_text="32 V",
        radius=80,
    )

    assert (
        "Smith et al. reported this result."
        in context
    )

    assert (
        "[TARGET_START]32 V[TARGET_END]"
        in context
    )


def test_context_can_cross_next_page(
    tmp_path,
    monkeypatch,
):
    install_test_database(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )

    context = build_provenance_context(
        document_id="doc-1",
        page_number=2,
        mention_key="p2:7:11",
        raw_text="32 V",
        radius=80,
    )

    assert (
        "NEXT-PAGE-THREE"
        in context
    )


def test_page_number_mismatch_is_rejected(
    tmp_path,
    monkeypatch,
):
    install_test_database(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )

    with pytest.raises(
        ValueError
    ):
        build_provenance_context(
            document_id="doc-1",
            page_number=2,
            mention_key="p1:7:11",
            raw_text="32 V",
            radius=80,
        )


def test_stale_offsets_are_rejected(
    tmp_path,
    monkeypatch,
):
    install_test_database(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )

    with pytest.raises(
        ValueError
    ):
        build_provenance_context(
            document_id="doc-1",
            page_number=2,
            mention_key="p2:7:11",
            raw_text="99 V",
            radius=80,
        )


def test_radius_must_be_positive(
    tmp_path,
    monkeypatch,
):
    install_test_database(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )

    with pytest.raises(
        ValueError
    ):
        build_provenance_context(
            document_id="doc-1",
            page_number=2,
            mention_key="p2:7:11",
            raw_text="32 V",
            radius=0,
        )
