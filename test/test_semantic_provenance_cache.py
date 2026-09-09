import sqlite3

from app.database import (
    enrichment_repository,
    sqlite_db,
)

from app.enrichment.metric_classifier import (
    CLASSIFIER_VERSION,
)

from app.enrichment.metric_ontology import (
    ONTOLOGY_VERSION,
)

from app.enrichment.numeric_scanner import (
    DETECTOR_VERSION,
)

from app.enrichment.provenance_classifier import (
    PROVENANCE_CLASSIFIER_VERSION,
)

from app.enrichment.provenance_ontology import (
    PROVENANCE_ONTOLOGY_VERSION,
)

from app.enrichment.semantic_provenance_classifier import (
    SEMANTIC_PROVENANCE_CLASSIFIER_VERSION,
)

from app.enrichment.unit_signature import (
    NORMALIZER_VERSION,
)


def install_test_database(
    *,
    tmp_path,
    monkeypatch,
):

    database_path = (
        tmp_path
        / "semantic-provenance-test.db"
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


def make_mention(
    *,
    mention_key: str,
    value: float,
    sentence: str,
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
            sentence,

        "context_text":
            sentence,
    }


def get_mention_id() -> int:

    rows = (
        enrichment_repository.get_numeric_mentions(
            document_id="doc-1",
            detector_version=(
                DETECTOR_VERSION
            ),
        )
    )

    assert len(rows) == 1

    return int(
        rows[0]["id"]
    )


def create_metric_classification() -> int:

    mention_id = (
        get_mention_id()
    )

    enrichment_repository.upsert_metric_classifications(
        [
            {
                "mention_id":
                    mention_id,

                "classifier_version":
                    CLASSIFIER_VERSION,

                "ontology_version":
                    ONTOLOGY_VERSION,

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
                CLASSIFIER_VERSION
            ),

            ontology_version=(
                ONTOLOGY_VERSION
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


def add_deterministic_provenance(
    *,
    metric_classification_id: int,
    status: str,
    provenance: str,
):

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
                    status,

                "provenance":
                    provenance,

                "method":
                    "deterministic",

                "score":
                    (
                        None
                        if status == "unresolved"
                        else 4
                    ),

                "candidates_json":
                    "[]",

                "reason":
                    (
                        "insufficient_provenance_context"
                        if status == "unresolved"
                        else
                        "unique_positive_provenance"
                    ),
            }
        ]
    )


def get_pending_rows():

    return (
        enrichment_repository.get_pending_semantic_provenance_input_rows(
            detector_version=(
                DETECTOR_VERSION
            ),

            metric_classifier_version=(
                CLASSIFIER_VERSION
            ),

            metric_ontology_version=(
                ONTOLOGY_VERSION
            ),

            normalizer_version=(
                NORMALIZER_VERSION
            ),

            deterministic_classifier_version=(
                PROVENANCE_CLASSIFIER_VERSION
            ),

            provenance_ontology_version=(
                PROVENANCE_ONTOLOGY_VERSION
            ),

            semantic_classifier_version=(
                SEMANTIC_PROVENANCE_CLASSIFIER_VERSION
            ),
        )
    )


def test_only_deterministic_unresolved_is_pending(
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
            make_mention(
                mention_key="p1:0:4",
                value=12.3,
                sentence=(
                    "The measured value "
                    "was 12.3 V."
                ),
            )
        ],
    )

    metric_classification_id = (
        create_metric_classification()
    )

    add_deterministic_provenance(
        metric_classification_id=(
            metric_classification_id
        ),
        status="unresolved",
        provenance="uncertain",
    )

    rows = get_pending_rows()

    assert len(rows) == 1

    assert (
        rows[0]["id"]
        == metric_classification_id
    )


def test_deterministic_classified_is_not_pending(
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
            make_mention(
                mention_key="p1:0:4",
                value=12.3,
                sentence=(
                    "We measured "
                    "12.3 V."
                ),
            )
        ],
    )

    metric_classification_id = (
        create_metric_classification()
    )

    add_deterministic_provenance(
        metric_classification_id=(
            metric_classification_id
        ),
        status="classified",
        provenance="author_result",
    )

    rows = get_pending_rows()

    assert rows == []


def test_existing_semantic_cache_is_not_pending(
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
            make_mention(
                mention_key="p1:0:4",
                value=12.3,
                sentence=(
                    "The measured value "
                    "was 12.3 V."
                ),
            )
        ],
    )

    metric_classification_id = (
        create_metric_classification()
    )

    add_deterministic_provenance(
        metric_classification_id=(
            metric_classification_id
        ),
        status="unresolved",
        provenance="uncertain",
    )

    assert len(
        get_pending_rows()
    ) == 1

    enrichment_repository.upsert_provenance_classifications(
        [
            {
                "metric_classification_id":
                    metric_classification_id,

                "provenance_classifier_version":
                    SEMANTIC_PROVENANCE_CLASSIFIER_VERSION,

                "provenance_ontology_version":
                    PROVENANCE_ONTOLOGY_VERSION,

                "status":
                    "classified",

                "provenance":
                    "author_result",

                "method":
                    "llm",

                "score":
                    None,

                "candidates_json":
                    (
                        '[{"provenance":'
                        '"author_result",'
                        '"confidence":0.95}]'
                    ),

                "reason":
                    (
                        "semantic_classified: "
                        "test"
                    ),
            }
        ]
    )

    assert (
        get_pending_rows()
        == []
    )
