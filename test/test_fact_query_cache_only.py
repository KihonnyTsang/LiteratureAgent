from unittest.mock import patch

from app.tools.fact_tool import (
    query_facts,
)


def test_query_facts_never_extracts_cache_miss(
):

    documents = [
        {
            "id":
                "doc_cached",

            "title":
                "Cached Paper",

            "filename":
                "cached.pdf",

            "local_path":
                "/tmp/cached.pdf",
        },

        {
            "id":
                "doc_missing",

            "title":
                "Missing Paper",

            "filename":
                "missing.pdf",

            "local_path":
                "/tmp/missing.pdf",
        },
    ]

    def cache_exists(
        *,
        document_id,
        metric_name,
        extraction_scope,
        extraction_version,
    ):

        return (
            document_id
            == "doc_cached"
        )

    with (
        patch(
            "app.tools.fact_tool."
            "select_documents",

            return_value=documents,
        ),

        patch(
            "app.tools.fact_tool."
            "ensure_facts_schema"
        ),

        patch(
            "app.tools.fact_tool."
            "has_cached_extraction",

            side_effect=cache_exists,
        ),

        patch(
            "app.tools.fact_tool."
            "load_cached_facts",

            # 0 facts 仍然是有效 cache。
            return_value=[],
        ) as load_cached_facts,

        patch(
            "app.tools.fact_tool."
            "extract_facts"
        ) as extract_facts,

        patch(
            "app.tools.fact_tool."
            "replace_facts_for_document_metric"
        ) as replace_facts,
    ):

        result = query_facts(
            metric="power_density",
            scope="all_documents",
            provenance_scope=(
                "author_results"
            ),
        )

    # --------------------------------------------------------
    # Cache semantics
    # --------------------------------------------------------

    load_cached_facts.assert_called_once()

    extract_facts.assert_not_called()

    replace_facts.assert_not_called()

    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    assert result.rows == []

    metadata = result.metadata

    assert (
        metadata[
            "document_count"
        ]
        == 2
    )

    assert (
        metadata[
            "cached_document_count"
        ]
        == 1
    )

    assert (
        metadata[
            "missing_document_count"
        ]
        == 1
    )

    assert (
        metadata[
            "cache_hit_count"
        ]
        == 1
    )

    assert (
        metadata[
            "extraction_count"
        ]
        == 0
    )

    assert (
        metadata[
            "coverage_complete"
        ]
        is False
    )

    assert (
        metadata[
            "coverage_ratio"
        ]
        == 0.5
    )