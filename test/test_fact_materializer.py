import sqlite3

import pytest

from app.database import (
    fact_repository,
)

from app.enrichment import (
    fact_materializer,
)

from app.enrichment.fact_materializer import (
    FACT_MATERIALIZER_SCOPE,
    FACT_MATERIALIZER_VERSION,
    build_materialized_fact,
    materialize_structured_facts,
    replace_materialized_facts,
    resolve_materialized_provenance,
)


def make_input_row(
    *,
    metric_key: str = "power",
    raw_value: float | None = 520.0,
    raw_unit: str = "mW",
    deterministic_status: str = "classified",
    deterministic_provenance: str = "author_result",
    semantic_status: str | None = None,
    semantic_provenance: str | None = None,
    semantic_candidates_json: str | None = None,
) -> dict:

    return {
        "metric_classification_id":
            1,

        "mention_id":
            1,

        "document_id":
            "doc-1",

        "page_number":
            1,

        "mention_key":
            "p1:10:16",

        "metric_key":
            metric_key,

        "raw_text":
            (
                f"{raw_value:g} {raw_unit}"
                if raw_value
                is not None
                else raw_unit
            ),

        "value_type":
            "scalar",

        "raw_value":
            raw_value,

        "raw_value_min":
            None,

        "raw_value_max":
            None,

        "raw_unit":
            raw_unit,

        "sentence_text":
            (
                f"The device produced "
                f"{raw_value:g} {raw_unit}."
                if raw_value
                is not None
                else raw_unit
            ),

        "context_text":
            "",

        "deterministic_status":
            deterministic_status,

        "deterministic_provenance":
            deterministic_provenance,

        "semantic_status":
            semantic_status,

        "semantic_provenance":
            semantic_provenance,

        "semantic_candidates_json":
            semantic_candidates_json,
    }


def test_deterministic_provenance_has_priority():

    row = make_input_row(
        deterministic_status=(
            "classified"
        ),

        deterministic_provenance=(
            "author_result"
        ),

        semantic_status=(
            "classified"
        ),

        semantic_provenance=(
            "cited_literature"
        ),

        semantic_candidates_json=(
            '[{"confidence":0.99}]'
        ),
    )

    provenance, source, confidence = (
        resolve_materialized_provenance(
            row
        )
    )

    assert provenance == "author_result"
    assert source == "deterministic"
    assert confidence is None


def test_semantic_fallback_is_used_after_deterministic_abstention():

    row = make_input_row(
        deterministic_status=(
            "unresolved"
        ),

        deterministic_provenance=(
            "uncertain"
        ),

        semantic_status=(
            "classified"
        ),

        semantic_provenance=(
            "cited_literature"
        ),

        semantic_candidates_json=(
            '[{"confidence":0.93}]'
        ),
    )

    provenance, source, confidence = (
        resolve_materialized_provenance(
            row
        )
    )

    assert (
        provenance
        == "cited_literature"
    )

    assert source == "semantic"
    assert confidence == 0.93


def test_unresolved_provenance_remains_uncertain():

    row = make_input_row(
        deterministic_status=(
            "unresolved"
        ),

        deterministic_provenance=(
            "uncertain"
        ),

        semantic_status=(
            "unresolved"
        ),

        semantic_provenance=(
            "uncertain"
        ),

        semantic_candidates_json=(
            '[{"confidence":0.6}]'
        ),
    )

    provenance, source, confidence = (
        resolve_materialized_provenance(
            row
        )
    )

    assert provenance == "uncertain"
    assert source == "unresolved"
    assert confidence == 0.6


def test_power_is_normalized_without_metric_specific_branch():

    fact = build_materialized_fact(
        make_input_row(
            metric_key="power",
            raw_value=520.0,
            raw_unit="mW",
        )
    )

    assert (
        fact["normalized_value"]
        == pytest.approx(
            0.52
        )
    )

    assert (
        fact["normalized_unit"]
        == "W"
    )

    assert (
        fact[
            "normalization_error"
        ]
        is None
    )


def test_power_density_is_normalized_from_pdf_style_unit():

    fact = build_materialized_fact(
        make_input_row(
            metric_key=(
                "power_density"
            ),
            raw_value=165.8,
            raw_unit="mW m−2",
        )
    )

    assert (
        fact["normalized_value"]
        == pytest.approx(
            0.1658
        )
    )

    assert (
        fact["normalized_unit"]
        == "W/m²"
    )


def test_evidence_verification_normalizes_whitespace():

    row = make_input_row(
        metric_key="current",
        raw_value=200.0,
        raw_unit="nA",
    )

    row["raw_text"] = (
        "200\nnA"
    )

    row["sentence_text"] = (
        "The maximum current "
        "was 200 nA."
    )

    fact = build_materialized_fact(
        row
    )

    assert (
        fact[
            "evidence_verified"
        ]
        == 1
    )


def install_test_database(
    *,
    tmp_path,
    monkeypatch,
):

    database_path = (
        tmp_path
        / "fact-materializer.db"
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
        fact_materializer,
        "get_connection",
        get_test_connection,
    )

    monkeypatch.setattr(
        fact_repository,
        "get_connection",
        get_test_connection,
    )

    connection = (
        get_test_connection()
    )

    try:
        connection.execute(
            """
            CREATE TABLE documents (
                id TEXT PRIMARY KEY,
                title TEXT,
                filename TEXT,
                local_path TEXT,
                page_count INTEGER,
                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,
                content_hash TEXT
            )
            """
        )

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

    return get_test_connection


def test_materialized_snapshot_is_idempotent(
    tmp_path,
    monkeypatch,
):

    get_test_connection = (
        install_test_database(
            tmp_path=tmp_path,
            monkeypatch=monkeypatch,
        )
    )

    fact = build_materialized_fact(
        make_input_row()
    )

    replace_materialized_facts(
        [
            fact,
        ]
    )

    replace_materialized_facts(
        [
            fact,
        ]
    )

    connection = (
        get_test_connection()
    )

    try:
        count = connection.execute(
            """
            SELECT COUNT(*)

            FROM facts

            WHERE extraction_scope = ?
              AND extraction_version = ?
            """,
            (
                FACT_MATERIALIZER_SCOPE,
                FACT_MATERIALIZER_VERSION,
            ),
        ).fetchone()[0]

    finally:
        connection.close()

    assert count == 1


def test_materialize_structured_facts_does_not_call_llm(
    monkeypatch,
):

    rows = [
        make_input_row(),
        make_input_row(
            metric_key=(
                "output_voltage"
            ),
            raw_value=12.0,
            raw_unit="V",
            deterministic_status=(
                "unresolved"
            ),
            deterministic_provenance=(
                "uncertain"
            ),
        ),
    ]

    monkeypatch.setattr(
        fact_materializer,
        "get_fact_materialization_input_rows",
        lambda: rows,
    )

    saved = []

    monkeypatch.setattr(
        fact_materializer,
        "replace_materialized_facts",
        lambda facts: saved.extend(
            facts
        ),
    )

    result = (
        materialize_structured_facts()
    )

    assert len(saved) == 2

    assert (
        result[
            "materialized_facts"
        ]
        == 2
    )

    assert (
        result[
            "author_result"
        ]
        == 1
    )

    assert (
        result[
            "uncertain"
        ]
        == 1
    )
