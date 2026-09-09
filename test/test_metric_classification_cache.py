import sqlite3

from app.database import (
    enrichment_repository,
    sqlite_db,
)


def install_test_database(
    *,
    tmp_path,
    monkeypatch,
):

    database_path = (
        tmp_path
        / "classification-test.db"
    )

    def get_test_connection():

        connection = sqlite3.connect(
            database_path
        )

        connection.execute(
            "PRAGMA foreign_keys = ON"
        )

        return connection

    monkeypatch.setattr(
        sqlite_db,
        "get_connection",
        get_test_connection,
    )

    monkeypatch.setattr(
        enrichment_repository,
        "get_connection",
        get_test_connection,
    )

    sqlite_db.init_db()

    connection = (
        get_test_connection()
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
                "doc-1",
                "Test document",
                "test.pdf",
                "/tmp/test.pdf",
                1,
                "hash-1",
            ),
        )

        connection.commit()

    finally:

        connection.close()


def make_voltage_mention(
    *,
    value: float,
    mention_key: str,
) -> dict:

    return {
        "page_number":
            1,

        "source_chunk_id":
            None,

        "mention_key":
            mention_key,

        "raw_text":
            f"{value:g} V",

        "value_type":
            "scalar",

        "raw_value":
            value,

        "raw_value_min":
            None,

        "raw_value_max":
            None,

        "raw_unit":
            "V",

        "sentence_text":
            (
                "The output voltage "
                f"reached {value:g} V."
            ),

        "context_text":
            (
                "The output voltage "
                f"reached {value:g} V."
            ),
    }


def test_metric_classification_upsert_is_idempotent(
    tmp_path,
    monkeypatch,
):

    install_test_database(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )

    enrichment_repository.replace_numeric_scan_result(
        document_id="doc-1",
        content_hash="hash-1",
        detector_version="numeric-v2",
        mentions=[
            make_voltage_mention(
                value=10.0,
                mention_key="p1:0:4",
            )
        ],
    )

    mentions = (
        enrichment_repository.get_numeric_mentions(
            document_id="doc-1",
            detector_version="numeric-v2",
        )
    )

    assert len(mentions) == 1

    mention_id = int(
        mentions[0]["id"]
    )

    base_record = {
        "mention_id":
            mention_id,

        "classifier_version":
            "metric-classifier-v1",

        "ontology_version":
            "metric-ontology-v1",

        "normalizer_version":
            "unit-signature-v2",

        "method":
            "deterministic",

        "candidates_json":
            "[]",
    }

    enrichment_repository.upsert_metric_classifications(
        [
            {
                **base_record,

                "status":
                    "unresolved",

                "metric_key":
                    None,

                "score":
                    0,

                "reason":
                    "insufficient_context",
            }
        ]
    )

    enrichment_repository.upsert_metric_classifications(
        [
            {
                **base_record,

                "status":
                    "classified",

                "metric_key":
                    "output_voltage",

                "score":
                    2,

                "reason":
                    "unique_positive_candidate",
            }
        ]
    )

    rows = (
        enrichment_repository.get_metric_classification_rows(
            detector_version="numeric-v2",

            classifier_version=(
                "metric-classifier-v1"
            ),

            ontology_version=(
                "metric-ontology-v1"
            ),

            normalizer_version=(
                "unit-signature-v2"
            ),
        )
    )

    assert len(rows) == 1

    assert (
        rows[0]["status"]
        == "classified"
    )

    assert (
        rows[0]["metric_key"]
        == "output_voltage"
    )

    assert (
        rows[0]["score"]
        == 2
    )


def test_numeric_rescan_cascades_old_classification(
    tmp_path,
    monkeypatch,
):

    install_test_database(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )

    enrichment_repository.replace_numeric_scan_result(
        document_id="doc-1",
        content_hash="hash-1",
        detector_version="numeric-v2",
        mentions=[
            make_voltage_mention(
                value=10.0,
                mention_key="p1:0:4",
            )
        ],
    )

    mentions = (
        enrichment_repository.get_numeric_mentions(
            document_id="doc-1",
            detector_version="numeric-v2",
        )
    )

    old_mention_id = int(
        mentions[0]["id"]
    )

    enrichment_repository.upsert_metric_classifications(
        [
            {
                "mention_id":
                    old_mention_id,

                "classifier_version":
                    "metric-classifier-v1",

                "ontology_version":
                    "metric-ontology-v1",

                "normalizer_version":
                    "unit-signature-v2",

                "status":
                    "classified",

                "metric_key":
                    "output_voltage",

                "method":
                    "deterministic",

                "score":
                    2,

                "candidates_json":
                    "[]",

                "reason":
                    "unique_positive_candidate",
            }
        ]
    )

    rows_before = (
        enrichment_repository.get_metric_classification_rows(
            detector_version="numeric-v2",
        )
    )

    assert len(rows_before) == 1

    # 模拟同一个 detector version
    # 对该文档重新扫描。
    #
    # replace_numeric_scan_result()
    # 会先 DELETE 旧 numeric_mentions，
    # FK ON DELETE CASCADE 应同步删除
    # 旧 classification。
    enrichment_repository.replace_numeric_scan_result(
        document_id="doc-1",
        content_hash="hash-2",
        detector_version="numeric-v2",
        mentions=[
            make_voltage_mention(
                value=20.0,
                mention_key="p1:10:14",
            )
        ],
    )

    rows_after = (
        enrichment_repository.get_metric_classification_rows(
            detector_version="numeric-v2",
        )
    )

    assert rows_after == []

    new_mentions = (
        enrichment_repository.get_numeric_mentions(
            document_id="doc-1",
            detector_version="numeric-v2",
        )
    )

    assert len(new_mentions) == 1

    assert (
        int(
            new_mentions[0]["id"]
        )
        != old_mention_id
    )