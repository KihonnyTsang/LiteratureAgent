import pytest

from app.database.sqlite_db import (
    get_all_documents,
)

from app.database.fact_repository import (
    ensure_facts_schema,
    get_saved_facts,
)


@pytest.mark.integration
def test_fact_repository_reads_saved_facts() -> None:
    """
    验证真实 SQLite 中已持久化的 Fact
    可以通过 Fact Repository 正确读取。

    这是只读 integration test。

    本测试故意不调用：

    - extract_facts()
    - replace_facts_for_document_metric()

    避免自动化测试修改正式知识库中的 facts。
    """

    ensure_facts_schema()

    documents = get_all_documents()

    assert documents

    target_document = next(
        (
            document
            for document
            in documents
            if "Siddiqui"
            in document["title"]
        ),
        None,
    )

    assert (
        target_document
        is not None
    )

    saved_facts = get_saved_facts(
        document_id=(
            target_document["id"]
        ),
        metric_name=(
            "power_density"
        ),
        extraction_scope=(
            "author_results"
        ),
    )

    assert saved_facts

    required_fields = {
        "title",
        "raw_value",
        "raw_unit",
        "normalized_value",
        "normalized_unit",
        "value_type",
        "provenance",
        "page_number",
        "source_chunk_id",
        "evidence_verified",
        "evidence",
    }

    for fact in saved_facts:

        assert (
            required_fields
            <= set(fact)
        )

        assert fact["title"]

        assert (
            fact["raw_value"]
            is not None
        )

        assert fact["raw_unit"]

        assert fact["value_type"]

        assert fact["provenance"]

        assert (
            fact["page_number"]
            is not None
        )

        assert fact["evidence"]