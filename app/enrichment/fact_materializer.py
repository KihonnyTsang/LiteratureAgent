import json
import re
import sqlite3

from collections import Counter
from typing import Any

from pint.errors import (
    DimensionalityError,
    UndefinedUnitError,
)

from app.database.fact_repository import (
    ensure_facts_schema,
)

from app.database.sqlite_db import (
    get_connection,
)

from app.enrichment.metric_classifier import (
    CLASSIFIER_VERSION,
)

from app.enrichment.metric_ontology import (
    ONTOLOGY_VERSION,
    get_metric_spec,
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

from app.extraction.unit_normalizer import (
    convert_number,
    normalize_unit_text,
)


FACT_MATERIALIZER_VERSION = (
    "structured-materializer-v1"
)

FACT_MATERIALIZER_SCOPE = (
    "structured_mentions"
)

_ALLOWED_CLASSIFIED_PROVENANCE = {
    "author_result",
    "cited_literature",
}


def _parse_semantic_confidence(
    candidates_json: str | None,
) -> float | None:
    """
    Read the semantic classifier's audit confidence.

    The confidence is audit metadata only. It is not used
    to decide whether a provenance label is accepted.
    """

    try:
        payload = json.loads(
            candidates_json
            or "[]"
        )
    except Exception:
        return None

    if (
        not isinstance(
            payload,
            list,
        )
        or
        not payload
        or
        not isinstance(
            payload[0],
            dict,
        )
    ):
        return None

    value = payload[0].get(
        "confidence"
    )

    if isinstance(
        value,
        (int, float),
    ):
        return float(value)

    return None


def resolve_materialized_provenance(
    row: dict[str, Any],
) -> tuple[
    str,
    str,
    float | None,
]:
    """
    Resolve the best currently cached provenance.

    Priority:
    1. deterministic classified result
    2. semantic v3 classified fallback
    3. uncertain

    No LLM is called here.
    """

    deterministic_status = (
        row.get(
            "deterministic_status"
        )
    )

    deterministic_provenance = (
        row.get(
            "deterministic_provenance"
        )
    )

    if (
        deterministic_status
        == "classified"
        and
        deterministic_provenance
        in _ALLOWED_CLASSIFIED_PROVENANCE
    ):
        return (
            deterministic_provenance,
            "deterministic",
            None,
        )

    semantic_status = (
        row.get(
            "semantic_status"
        )
    )

    semantic_provenance = (
        row.get(
            "semantic_provenance"
        )
    )

    if (
        semantic_status
        == "classified"
        and
        semantic_provenance
        in _ALLOWED_CLASSIFIED_PROVENANCE
    ):
        return (
            semantic_provenance,
            "semantic",
            _parse_semantic_confidence(
                row.get(
                    "semantic_candidates_json"
                )
            ),
        )

    return (
        "uncertain",
        "unresolved",
        _parse_semantic_confidence(
            row.get(
                "semantic_candidates_json"
            )
        ),
    )


def _normalize_whitespace(
    text: str | None,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        text
        or "",
    ).strip()


def _normalize_materialized_values(
    *,
    metric_key: str,
    value_type: str,
    raw_value: float | None,
    raw_value_min: float | None,
    raw_value_max: float | None,
    raw_unit: str | None,
) -> dict[str, Any]:
    """
    Normalize one metric-classified numeric mention using
    Metric Ontology v1 as the source of canonical units.

    This function contains no metric-specific branches.
    """

    metric_spec = get_metric_spec(
        metric_key
    )

    canonical_unit = (
        metric_spec.canonical_unit
    )

    if (
        not raw_unit
        or
        not canonical_unit
    ):
        return {
            "normalized_value":
                raw_value,

            "normalized_value_min":
                raw_value_min,

            "normalized_value_max":
                raw_value_max,

            "normalized_unit":
                raw_unit,

            "normalization_converted":
                0,

            "normalization_error":
                (
                    "missing raw or canonical unit"
                ),
        }

    from_unit = normalize_unit_text(
        raw_unit
    )

    to_unit = normalize_unit_text(
        canonical_unit
    )

    try:
        return {
            "normalized_value":
                convert_number(
                    raw_value,
                    from_unit,
                    to_unit,
                ),

            "normalized_value_min":
                convert_number(
                    raw_value_min,
                    from_unit,
                    to_unit,
                ),

            "normalized_value_max":
                convert_number(
                    raw_value_max,
                    from_unit,
                    to_unit,
                ),

            "normalized_unit":
                canonical_unit,

            "normalization_converted":
                1,

            "normalization_error":
                None,
        }

    except (
        UndefinedUnitError,
        DimensionalityError,
        ValueError,
    ) as error:
        return {
            "normalized_value":
                raw_value,

            "normalized_value_min":
                raw_value_min,

            "normalized_value_max":
                raw_value_max,

            "normalized_unit":
                raw_unit,

            "normalization_converted":
                0,

            "normalization_error":
                str(error),
        }


def build_materialized_fact(
    row: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert one cached metric-classified numeric mention into
    a structured fact row.

    This step:
    - does not scan PDFs,
    - does not query Qdrant,
    - does not call an LLM,
    - does not contain metric-specific logic.
    """

    provenance, provenance_source, confidence = (
        resolve_materialized_provenance(
            row
        )
    )

    normalized = (
        _normalize_materialized_values(
            metric_key=(
                row["metric_key"]
            ),

            value_type=(
                row.get(
                    "value_type"
                )
                or
                "scalar"
            ),

            raw_value=(
                row.get(
                    "raw_value"
                )
            ),

            raw_value_min=(
                row.get(
                    "raw_value_min"
                )
            ),

            raw_value_max=(
                row.get(
                    "raw_value_max"
                )
            ),

            raw_unit=(
                row.get(
                    "raw_unit"
                )
            ),
        )
    )

    evidence = (
        row.get(
            "sentence_text"
        )
        or
        row.get(
            "context_text"
        )
        or
        row.get(
            "raw_text"
        )
        or
        ""
    )

    evidence_verified = int(
        _normalize_whitespace(
            row.get(
                "raw_text"
            )
        )
        in
        _normalize_whitespace(
            evidence
        )
    )

    return {
        "document_id":
            row["document_id"],

        "metric_name":
            row["metric_key"],

        "value_type":
            (
                row.get(
                    "value_type"
                )
                or
                "scalar"
            ),

        "raw_value":
            row.get(
                "raw_value"
            ),

        "raw_value_min":
            row.get(
                "raw_value_min"
            ),

        "raw_value_max":
            row.get(
                "raw_value_max"
            ),

        "raw_unit":
            row.get(
                "raw_unit"
            ),

        "normalized_value":
            normalized[
                "normalized_value"
            ],

        "normalized_value_min":
            normalized[
                "normalized_value_min"
            ],

        "normalized_value_max":
            normalized[
                "normalized_value_max"
            ],

        "normalized_unit":
            normalized[
                "normalized_unit"
            ],

        "normalization_converted":
            normalized[
                "normalization_converted"
            ],

        "normalization_error":
            normalized[
                "normalization_error"
            ],

        "page_number":
            row.get(
                "page_number"
            ),

        "source_chunk_id":
            None,

        "evidence":
            evidence,

        "evidence_verified":
            evidence_verified,

        "condition_text":
            None,

        "provenance":
            provenance,

        "confidence":
            confidence,

        "extraction_scope":
            FACT_MATERIALIZER_SCOPE,

        "extraction_version":
            FACT_MATERIALIZER_VERSION,

        # Returned for statistics/audit only.
        "_provenance_source":
            provenance_source,
    }


def get_fact_materialization_input_rows(
) -> list[dict[str, Any]]:
    """
    Load every currently metric-classified Numeric Mention.

    Deterministic provenance is complete for this universe.
    Semantic Provenance v3 is joined only as an optional
    fallback cache.
    """

    connection = get_connection()

    connection.row_factory = (
        sqlite3.Row
    )

    try:
        rows = connection.execute(
            """
            SELECT
                nmc.id
                    AS metric_classification_id,

                nmc.metric_key
                    AS metric_key,

                nm.id
                    AS mention_id,

                nm.document_id
                    AS document_id,

                nm.page_number
                    AS page_number,

                nm.mention_key
                    AS mention_key,

                nm.raw_text
                    AS raw_text,

                nm.value_type
                    AS value_type,

                nm.raw_value
                    AS raw_value,

                nm.raw_value_min
                    AS raw_value_min,

                nm.raw_value_max
                    AS raw_value_max,

                nm.raw_unit
                    AS raw_unit,

                nm.sentence_text
                    AS sentence_text,

                nm.context_text
                    AS context_text,

                deterministic.status
                    AS deterministic_status,

                deterministic.provenance
                    AS deterministic_provenance,

                deterministic.method
                    AS deterministic_method,

                deterministic.reason
                    AS deterministic_reason,

                semantic.status
                    AS semantic_status,

                semantic.provenance
                    AS semantic_provenance,

                semantic.method
                    AS semantic_method,

                semantic.candidates_json
                    AS semantic_candidates_json,

                semantic.reason
                    AS semantic_reason

            FROM numeric_metric_classifications
                AS nmc

            JOIN numeric_mentions
                AS nm
              ON nm.id =
                 nmc.mention_id

            JOIN numeric_provenance_classifications
                AS deterministic
              ON deterministic.metric_classification_id =
                 nmc.id

             AND deterministic.provenance_classifier_version = ?

             AND deterministic.provenance_ontology_version = ?

            LEFT JOIN numeric_provenance_classifications
                AS semantic
              ON semantic.metric_classification_id =
                 nmc.id

             AND semantic.provenance_classifier_version = ?

             AND semantic.provenance_ontology_version = ?

            WHERE nm.detector_version = ?

              AND nmc.classifier_version = ?

              AND nmc.ontology_version = ?

              AND nmc.normalizer_version = ?

              AND nmc.status = 'classified'

            ORDER BY
                nm.document_id,
                nm.page_number,
                nm.id
            """,
            (
                PROVENANCE_CLASSIFIER_VERSION,
                PROVENANCE_ONTOLOGY_VERSION,

                SEMANTIC_PROVENANCE_CLASSIFIER_VERSION,
                PROVENANCE_ONTOLOGY_VERSION,

                DETECTOR_VERSION,
                CLASSIFIER_VERSION,
                ONTOLOGY_VERSION,
                NORMALIZER_VERSION,
            ),
        ).fetchall()

        return [
            dict(row)
            for row
            in rows
        ]

    finally:
        connection.close()


def replace_materialized_facts(
    facts: list[dict[str, Any]],
) -> None:
    """
    Atomically replace the complete Structured Fact
    Materializer v1 snapshot.

    Other fact extraction versions are left untouched.
    """

    ensure_facts_schema()

    connection = get_connection()

    try:
        connection.execute(
            "BEGIN"
        )

        connection.execute(
            """
            DELETE FROM facts

            WHERE extraction_scope = ?
              AND extraction_version = ?
            """,
            (
                FACT_MATERIALIZER_SCOPE,
                FACT_MATERIALIZER_VERSION,
            ),
        )

        records = [
            (
                fact[
                    "document_id"
                ],

                fact[
                    "metric_name"
                ],

                fact[
                    "value_type"
                ],

                fact.get(
                    "raw_value"
                ),

                fact.get(
                    "raw_value_min"
                ),

                fact.get(
                    "raw_value_max"
                ),

                fact.get(
                    "raw_unit"
                ),

                fact.get(
                    "normalized_value"
                ),

                fact.get(
                    "normalized_value_min"
                ),

                fact.get(
                    "normalized_value_max"
                ),

                fact.get(
                    "normalized_unit"
                ),

                fact.get(
                    "normalization_converted",
                    0,
                ),

                fact.get(
                    "normalization_error"
                ),

                fact.get(
                    "page_number"
                ),

                fact.get(
                    "source_chunk_id"
                ),

                fact.get(
                    "evidence"
                ),

                fact.get(
                    "evidence_verified",
                    0,
                ),

                fact.get(
                    "condition_text"
                ),

                fact[
                    "provenance"
                ],

                fact.get(
                    "confidence"
                ),

                FACT_MATERIALIZER_SCOPE,
                FACT_MATERIALIZER_VERSION,
            )
            for fact
            in facts
        ]

        if records:
            connection.executemany(
                """
                INSERT INTO facts (
                    document_id,
                    metric_name,
                    value_type,

                    raw_value,
                    raw_value_min,
                    raw_value_max,
                    raw_unit,

                    normalized_value,
                    normalized_value_min,
                    normalized_value_max,
                    normalized_unit,

                    normalization_converted,
                    normalization_error,

                    page_number,
                    source_chunk_id,

                    evidence,
                    evidence_verified,
                    condition_text,

                    provenance,
                    confidence,

                    extraction_scope,
                    extraction_version
                )

                VALUES (
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    ?, ?,
                    ?, ?
                )
                """,
                records,
            )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def get_materialized_fact_rows(
) -> list[dict[str, Any]]:

    ensure_facts_schema()

    connection = get_connection()

    connection.row_factory = (
        sqlite3.Row
    )

    try:
        rows = connection.execute(
            """
            SELECT *

            FROM facts

            WHERE extraction_scope = ?
              AND extraction_version = ?

            ORDER BY
                document_id,
                page_number,
                id
            """,
            (
                FACT_MATERIALIZER_SCOPE,
                FACT_MATERIALIZER_VERSION,
            ),
        ).fetchall()

        return [
            dict(row)
            for row
            in rows
        ]

    finally:
        connection.close()


def materialize_structured_facts(
) -> dict[str, Any]:
    """
    Rebuild the current structured fact snapshot.

    This is an offline deterministic operation.
    No DeepSeek call is made.
    """

    input_rows = (
        get_fact_materialization_input_rows()
    )

    facts = [
        build_materialized_fact(
            row
        )
        for row
        in input_rows
    ]

    replace_materialized_facts(
        facts
    )

    provenance_counts = Counter(
        fact[
            "provenance"
        ]
        for fact
        in facts
    )

    provenance_source_counts = Counter(
        fact[
            "_provenance_source"
        ]
        for fact
        in facts
    )

    metric_counts = Counter(
        fact[
            "metric_name"
        ]
        for fact
        in facts
    )

    normalization_error_count = sum(
        1
        for fact
        in facts
        if fact.get(
            "normalization_error"
        )
    )

    return {
        "materializer_version":
            FACT_MATERIALIZER_VERSION,

        "materializer_scope":
            FACT_MATERIALIZER_SCOPE,

        "detector_version":
            DETECTOR_VERSION,

        "metric_classifier_version":
            CLASSIFIER_VERSION,

        "metric_ontology_version":
            ONTOLOGY_VERSION,

        "unit_signature_version":
            NORMALIZER_VERSION,

        "deterministic_provenance_version":
            PROVENANCE_CLASSIFIER_VERSION,

        "semantic_provenance_version":
            SEMANTIC_PROVENANCE_CLASSIFIER_VERSION,

        "provenance_ontology_version":
            PROVENANCE_ONTOLOGY_VERSION,

        "input_metric_classified_mentions":
            len(
                input_rows
            ),

        "materialized_facts":
            len(
                facts
            ),

        "author_result":
            provenance_counts.get(
                "author_result",
                0,
            ),

        "cited_literature":
            provenance_counts.get(
                "cited_literature",
                0,
            ),

        "uncertain":
            provenance_counts.get(
                "uncertain",
                0,
            ),

        "deterministic_provenance":
            provenance_source_counts.get(
                "deterministic",
                0,
            ),

        "semantic_provenance":
            provenance_source_counts.get(
                "semantic",
                0,
            ),

        "unresolved_provenance":
            provenance_source_counts.get(
                "unresolved",
                0,
            ),

        "normalization_errors":
            normalization_error_count,

        "metric_counts":
            dict(
                sorted(
                    metric_counts.items()
                )
            ),
    }
