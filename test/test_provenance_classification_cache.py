import sqlite3

from app.database import (
    enrichment_repository,
    sqlite_db,
)


DETECTOR_VERSION = "numeric-v2"
METRIC_CLASSIFIER_VERSION = (
    "metric-classifier-v1"
)
METRIC_ONTOLOGY_VERSION = (
    "metric-ontology-v1"
)
NORMALIZER_VERSION = (
    "unit-signature-v2"
)
PROVENANCE_CLASSIFIER_VERSION = (
    "provenance-classifier-v1"
)
PROVENANCE_ONTOLOGY_VERSION = (
    "provenance-ontology-v1"
)


def install_test_database(
    *,
    tmp_path,
    monkeypatch,
):

    database_path = (
        tmp_path
        / "provenance-test.db"
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


def make_numeric_mention(
    *,
    value: float,
    mention_key: str,
    sentence_text: str,
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
            sentence_text,

        "context_text":
            sentence_text,
    }


def create_metric_classification(
    *,
    document_id: str,
) -> int:

    mentions = (
        enrichment_repository.get_numeric_mentions(
            document_id=document_id,
            detector_version=(
                DETECTOR_VERSION
            ),
        )
    )

    mention_id = int(
        mentions[0]["id"]
    )

    enrichment_repository.upsert_metric_classifications(
        [
            {
                "mention_id":
                    mention_id,

                "classifier_version":
                    METRIC_CLASSIFIER_VERSION,

                "ontology_version":
                    METRIC_ONTOLOGY_VERSION,

                "normalizer_version":
                    NORMALIZER_VERSION,

                "status":
                    "classified",

                "metric_key":
                    "output_voltage",

                "method":
                    "deterministic",

                "score":
                    4,

                "candidates_json":
                    "[]",

                "reason":
                    "unique_positive_candidate",
            }
        ]
    )

    rows = (
        enrichment_repository.get_metric_classification_rows(
            detector_version=(
                DETECTOR_VERSION
            ),

            classifier_version=(
                METRIC_CLASSIFIER_VERSION
            ),

            ontology_version=(
                METRIC_ONTOLOGY_VERSION
            ),

            normalizer_version=(
                NORMALIZER_VERSION
            ),
        )
    )

    assert len(rows) == 1

    return int(
        rows[0]["id"]
    )


def test_provenance_upsert_is_idempotent(
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
        detector_version=(
            DETECTOR_VERSION
        ),
        mentions=[
            make_numeric_mention(
                value=10.0,
                mention_key="p1:0:4",
                sentence_text=(
                    "We measured a value "
                    "of 10 V."
                ),
            )
        ],
    )

    metric_classification_id = (
        create_metric_classification(
            document_id="doc-1"
        )
    )

    base_record = {
        "metric_classification_id":
            metric_classification_id,

        "provenance_classifier_version":
            PROVENANCE_CLASSIFIER_VERSION,

        "provenance_ontology_version":
            PROVENANCE_ONTOLOGY_VERSION,

        "method":
            "deterministic",

        "candidates_json":
            "[]",
    }

    enrichment_repository.upsert_provenance_classifications(
        [
            {
                **base_record,

                "status":
                    "unresolved",

                "provenance":
                    "uncertain",

                "score":
                    0,

                "reason":
                    (
                        "insufficient_"
                        "provenance_context"
                    ),
            }
        ]
    )

    enrichment_repository.upsert_provenance_classifications(
        [
            {
                **base_record,

                "status":
                    "classified",

                "provenance":
                    "author_result",

                "score":
                    4,

                "reason":
                    (
                        "unique_positive_"
                        "provenance"
                    ),
            }
        ]
    )

    rows = (
        enrichment_repository.get_provenance_classification_rows(
            detector_version=(
                DETECTOR_VERSION
            ),

            metric_classifier_version=(
                METRIC_CLASSIFIER_VERSION
            ),

            ontology_version=(
                METRIC_ONTOLOGY_VERSION
            ),

            normalizer_version=(
                NORMALIZER_VERSION
            ),

            provenance_classifier_version=(
                PROVENANCE_CLASSIFIER_VERSION
            ),

            provenance_ontology_version=(
                PROVENANCE_ONTOLOGY_VERSION
            ),
        )
    )

    assert len(rows) == 1

    assert (
        rows[0]["status"]
        == "classified"
    )

    assert (
        rows[0]["provenance"]
        == "author_result"
    )

    assert (
        rows[0]["score"]
        == 4
    )


def test_numeric_rescan_cascades_provenance_cache(
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
        detector_version=(
            DETECTOR_VERSION
        ),
        mentions=[
            make_numeric_mention(
                value=10.0,
                mention_key="p1:0:4",
                sentence_text=(
                    "We measured a value "
                    "of 10 V."
                ),
            )
        ],
    )

    metric_classification_id = (
        create_metric_classification(
            document_id="doc-1"
        )
    )

    enrichment_repository.upsert_provenance_classifications(
        [
            {
                "metric_classification_id":
                    metric_classification_id,

                "provenance_classifier_version":
                    PROVENANCE_CLASSIFIER_VERSION,

                "provenance_ontology_version":
                    PROVENANCE_ONTOLOGY_VERSION,

                "status":
                    "classified",

                "provenance":
                    "author_result",

                "method":
                    "deterministic",

                "score":
                    4,

                "candidates_json":
                    "[]",

                "reason":
                    (
                        "unique_positive_"
                        "provenance"
                    ),
            }
        ]
    )

    rows_before = (
        enrichment_repository.get_provenance_classification_rows(
            detector_version=(
                DETECTOR_VERSION
            ),
        )
    )

    assert len(rows_before) == 1

    # Numeric Mention 被重新扫描删除：
    #
    # numeric_mentions
    #     ↓ cascade
    # numeric_metric_classifications
    #     ↓ cascade
    # numeric_provenance_classifications
    enrichment_repository.replace_numeric_scan_result(
        document_id="doc-1",
        content_hash="hash-2",
        detector_version=(
            DETECTOR_VERSION
        ),
        mentions=[
            make_numeric_mention(
                value=20.0,
                mention_key="p1:10:14",
                sentence_text=(
                    "We measured a value "
                    "of 20 V."
                ),
            )
        ],
    )

    rows_after = (
        enrichment_repository.get_provenance_classification_rows(
            detector_version=(
                DETECTOR_VERSION
            ),
        )
    )

    assert rows_after == []