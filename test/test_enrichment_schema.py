from pathlib import Path

from app.database import sqlite_db

from app.database.enrichment_repository import (
    get_document_bibliography,
    get_journal_metrics,
    get_numeric_mentions,
    replace_numeric_mentions_for_document,
    upsert_document_bibliography,
    upsert_journal_metric,
)


def prepare_database(
    tmp_path: Path,
    monkeypatch,
) -> None:

    database_path = (
        tmp_path
        / "literature.db"
    )

    monkeypatch.setattr(
        sqlite_db,
        "DB_PATH",
        database_path,
    )

    sqlite_db.init_db()

    connection = (
        sqlite_db.get_connection()
    )

    try:

        connection.execute(
            """
            INSERT INTO documents (
                id,
                title,
                filename,
                local_path,
                page_count,
                content_hash
            )

            VALUES (
                ?, ?, ?, ?, ?, ?
            )
            """,
            (
                "doc_test",
                "Temporary Title",
                "paper.pdf",
                "/tmp/paper.pdf",
                1,
                "hash_test",
            ),
        )

        connection.execute(
            """
            INSERT INTO chunks (
                document_id,
                page_number,
                chunk_index,
                text
            )

            VALUES (
                ?, ?, ?, ?
            )
            """,
            (
                "doc_test",
                1,
                0,
                (
                    "The power density "
                    "was 41.02 μW/cm²."
                ),
            ),
        )

        connection.commit()

    finally:

        connection.close()


def test_bibliography_upsert(
    tmp_path,
    monkeypatch,
):

    prepare_database(
        tmp_path,
        monkeypatch,
    )

    upsert_document_bibliography(
        document_id="doc_test",
        doi="10.1000/test",
        title="Resolved Paper Title",
        authors=[
            "Author A",
            "Author B",
        ],
        publication_year=2024,
        journal_name="Example Journal",
        issn="1234-5678",
        source="test",
        metadata_version="v1",
    )

    bibliography = (
        get_document_bibliography(
            "doc_test"
        )
    )

    assert bibliography is not None

    assert (
        bibliography["doi"]
        == "10.1000/test"
    )

    assert (
        bibliography["title"]
        == "Resolved Paper Title"
    )

    assert (
        bibliography["authors"]
        == [
            "Author A",
            "Author B",
        ]
    )

    assert (
        bibliography["journal_name"]
        == "Example Journal"
    )


def test_journal_metric_upsert(
    tmp_path,
    monkeypatch,
):

    prepare_database(
        tmp_path,
        monkeypatch,
    )

    upsert_journal_metric(
        journal_key="issn:1234-5678",
        journal_name="Example Journal",
        issn="1234-5678",
        metric_key="sciif",
        metric_value_text="9.5",
        metric_value_number=9.5,
        metric_year=2025,
        source="test",
    )

    upsert_journal_metric(
        journal_key="issn:1234-5678",
        journal_name="Example Journal",
        issn="1234-5678",
        metric_key="sci",
        metric_value_text="Q1",
        metric_year=2025,
        source="test",
    )

    metrics = get_journal_metrics(
        "issn:1234-5678"
    )

    assert len(metrics) == 2

    metrics_by_key = {
        item["metric_key"]:
            item
        for item in metrics
    }

    assert (
        metrics_by_key[
            "sciif"
        ][
            "metric_value_number"
        ]
        == 9.5
    )

    assert (
        metrics_by_key[
            "sci"
        ][
            "metric_value_text"
        ]
        == "Q1"
    )


def test_numeric_mentions_replace(
    tmp_path,
    monkeypatch,
):

    prepare_database(
        tmp_path,
        monkeypatch,
    )

    connection = (
        sqlite_db.get_connection()
    )

    try:

        chunk_id = (
            connection.execute(
                """
                SELECT id
                FROM chunks
                WHERE document_id = ?
                """,
                (
                    "doc_test",
                ),
            )
            .fetchone()[0]
        )

    finally:

        connection.close()

    replace_numeric_mentions_for_document(
        document_id="doc_test",
        detector_version="v1",
        mentions=[
            {
                "page_number":
                    1,

                "source_chunk_id":
                    chunk_id,

                "mention_key":
                    "page1-span1",

                "raw_text":
                    "41.02 μW/cm²",

                "raw_value":
                    41.02,

                "raw_unit":
                    "μW/cm²",

                "sentence_text":
                    (
                        "The power density "
                        "was 41.02 μW/cm²."
                    ),

                "context_text":
                    (
                        "The power density "
                        "was 41.02 μW/cm²."
                    ),
            }
        ],
    )

    mentions = get_numeric_mentions(
        document_id="doc_test",
        detector_version="v1",
    )

    assert len(mentions) == 1

    assert (
        mentions[0][
            "raw_value"
        ]
        == 41.02
    )

    assert (
        mentions[0][
            "raw_unit"
        ]
        == "μW/cm²"
    )

    # 同版本 replacement 必须幂等。
    replace_numeric_mentions_for_document(
        document_id="doc_test",
        detector_version="v1",
        mentions=[],
    )

    assert (
        get_numeric_mentions(
            document_id="doc_test",
            detector_version="v1",
        )
        == []
    )


def test_enrichment_cascades_with_document_delete(
    tmp_path,
    monkeypatch,
):

    prepare_database(
        tmp_path,
        monkeypatch,
    )

    upsert_document_bibliography(
        document_id="doc_test",
        title="Paper",
    )

    replace_numeric_mentions_for_document(
        document_id="doc_test",
        detector_version="v1",
        mentions=[
            {
                "page_number":
                    1,

                "mention_key":
                    "mention-1",

                "raw_text":
                    "5 N",

                "raw_value":
                    5.0,

                "raw_unit":
                    "N",
            }
        ],
    )

    connection = (
        sqlite_db.get_connection()
    )

    try:

        connection.execute(
            """
            DELETE FROM documents
            WHERE id = ?
            """,
            (
                "doc_test",
            ),
        )

        connection.commit()

    finally:

        connection.close()

    assert (
        get_document_bibliography(
            "doc_test"
        )
        is None
    )

    assert (
        get_numeric_mentions(
            document_id="doc_test",
        )
        == []
    )