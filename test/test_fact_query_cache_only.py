from unittest.mock import patch

import pytest

from app.tools.fact_tool import (
    query_facts,
    resolve_online_metric_spec,
    structured_fact_to_tool_row,
)


def make_fact_row(
    *,
    document_id: str,
    title: str,
    provenance: str,
    value: float = 1.0,
    unit: str = "W",
    normalization_error: str | None = None,
) -> dict:
    return {
        "document_id": document_id,
        "title": title,
        "metric_name": "power",
        "value_type": "scalar",
        "raw_value": value,
        "raw_value_min": None,
        "raw_value_max": None,
        "raw_unit": unit,
        "normalized_value": value,
        "normalized_value_min": None,
        "normalized_value_max": None,
        "normalized_unit": unit,
        "normalization_error": normalization_error,
        "page_number": 1,
        "source_chunk_id": None,
        "evidence": "The device produced power.",
        "evidence_verified": 1,
        "condition_text": None,
        "provenance": provenance,
        "confidence": 0.95,
    }


def test_online_metric_resolution_uses_ontology_without_llm():
    with patch(
        "app.tools.fact_tool.resolve_metric_spec"
    ) as dynamic_resolver:
        spec = resolve_online_metric_spec(
            "output power"
        )

    dynamic_resolver.assert_not_called()

    assert spec.key == "power"
    assert spec.canonical_unit == "W"


def test_query_facts_reads_structured_snapshot_only():
    documents = [
        {"id": "doc-1", "title": "Paper One"},
        {"id": "doc-2", "title": "Paper Two"},
    ]

    materialized_rows = [
        make_fact_row(
            document_id="doc-1",
            title="Paper One",
            provenance="author_result",
            value=5.0,
        ),
        make_fact_row(
            document_id="doc-2",
            title="Paper Two",
            provenance="cited_literature",
            value=9.0,
        ),
        make_fact_row(
            document_id="doc-2",
            title="Paper Two",
            provenance="uncertain",
            value=12.0,
        ),
    ]

    with (
        patch(
            "app.tools.fact_tool.select_documents",
            return_value=documents,
        ),
        patch(
            "app.tools.fact_tool.structured_fact_snapshot_exists",
            return_value=True,
        ),
        patch(
            "app.tools.fact_tool.load_structured_fact_rows",
            return_value=materialized_rows,
        ) as load_rows,
        patch(
            "app.tools.fact_tool.extract_facts"
        ) as extract_facts,
        patch(
            "app.tools.fact_tool.replace_facts_for_document_metric"
        ) as replace_facts,
        patch(
            "app.tools.fact_tool.resolve_metric_spec"
        ) as dynamic_resolver,
    ):
        result = query_facts(
            metric="power",
            scope="all_documents",
            provenance_scope="author_results",
        )

    load_rows.assert_called_once_with(
        metric_key="power"
    )

    extract_facts.assert_not_called()
    replace_facts.assert_not_called()
    dynamic_resolver.assert_not_called()

    assert len(result.rows) == 1
    assert result.rows[0]["document_id"] == "doc-1"

    metadata = result.metadata

    assert metadata["source"] == "structured_facts"
    assert metadata["extraction_count"] == 0
    assert metadata["candidate_fact_count"] == 3
    assert metadata["author_result_count"] == 1
    assert metadata["cited_literature_count"] == 1
    assert metadata["uncertain_count"] == 1

    assert (
        metadata["provenance_coverage_ratio"]
        == pytest.approx(2 / 3)
    )

    assert metadata["coverage_complete"] is False


def test_all_mentions_preserves_uncertain_and_cited_rows():
    documents = [
        {"id": "doc-1", "title": "Paper One"},
    ]

    materialized_rows = [
        make_fact_row(
            document_id="doc-1",
            title="Paper One",
            provenance="author_result",
            value=1.0,
        ),
        make_fact_row(
            document_id="doc-1",
            title="Paper One",
            provenance="cited_literature",
            value=2.0,
        ),
        make_fact_row(
            document_id="doc-1",
            title="Paper One",
            provenance="uncertain",
            value=3.0,
        ),
    ]

    with (
        patch(
            "app.tools.fact_tool.select_documents",
            return_value=documents,
        ),
        patch(
            "app.tools.fact_tool.structured_fact_snapshot_exists",
            return_value=True,
        ),
        patch(
            "app.tools.fact_tool.load_structured_fact_rows",
            return_value=materialized_rows,
        ),
    ):
        result = query_facts(
            metric="power",
            provenance_scope="all_mentions",
        )

    assert len(result.rows) == 3

    assert {
        row["provenance"]
        for row in result.rows
    } == {
        "author_result",
        "cited_literature",
        "uncertain",
    }

    assert result.metadata["coverage_complete"] is True


def test_normalization_error_is_not_comparable():
    spec = resolve_online_metric_spec(
        "power"
    )

    row = make_fact_row(
        document_id="doc-1",
        title="Paper One",
        provenance="author_result",
        value=10.0,
        unit="W",
        normalization_error="unit mismatch",
    )

    result = structured_fact_to_tool_row(
        fact_row=row,
        metric_spec=spec,
    )

    assert result["value"] is None
    assert result["value_min"] is None
    assert result["value_max"] is None
    assert result["unit"] is None
    assert result["raw_value"] == 10.0
    assert result["normalization_error"] == "unit mismatch"


def test_missing_snapshot_is_reported_without_extraction():
    documents = [
        {"id": "doc-1", "title": "Paper One"},
        {"id": "doc-2", "title": "Paper Two"},
    ]

    with (
        patch(
            "app.tools.fact_tool.select_documents",
            return_value=documents,
        ),
        patch(
            "app.tools.fact_tool.structured_fact_snapshot_exists",
            return_value=False,
        ),
        patch(
            "app.tools.fact_tool.load_structured_fact_rows"
        ) as load_rows,
        patch(
            "app.tools.fact_tool.extract_facts"
        ) as extract_facts,
    ):
        result = query_facts(
            metric="power"
        )

    load_rows.assert_not_called()
    extract_facts.assert_not_called()

    assert result.rows == []
    assert result.metadata["cache_hit_count"] == 0
    assert result.metadata["missing_document_count"] == 2
    assert result.metadata["coverage_complete"] is False
    assert result.metadata["coverage_ratio"] == 0.0


def test_invalid_provenance_scope_is_rejected():
    with pytest.raises(ValueError):
        query_facts(
            metric="power",
            provenance_scope="not-a-scope",
        )
