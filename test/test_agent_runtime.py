import pytest

from app.agent.runtime import (
    run_agent,
)


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.slow
def test_runtime_grounded_rag() -> None:
    """
    完整 RAG Runtime 集成测试。

    会真实使用：

    - Planner LLM
    - Embedding
    - Qdrant
    - RAG
    - Answer generation

    因此属于：
    integration + llm + slow
    """

    result = run_agent(
        "为什么加入 BaTiO3 后"
        "压电输出会增强？"
    )

    assert (
        result.result_type
        == "grounded_text"
    )

    assert (
        result.text_result
        is not None
    )

    assert (
        result.final_answer
        is None
    )

    assert (
        result.text_result.text
    )

    assert (
        result.text_result.sources
    )

    assert (
        result.plan.steps[
            0
        ].tool
        == "rag_search"
    )


@pytest.mark.integration
@pytest.mark.llm
def test_runtime_structured_metadata() -> None:
    """
    完整 Structured Runtime 集成测试。

    会真实使用：

    - Planner LLM
    - SQLite Metadata Tool
    - Executor
    - Answer Writer
    - Deterministic Renderer
    """

    result = run_agent(
        "按页数从多到少排列"
        "所有论文"
    )

    assert (
        result.result_type
        == "structured"
    )

    assert (
        result.final_answer
        is not None
    )

    assert (
        result.text_result
        is None
    )

    assert (
        result.final_answer.table_rows
    )

    tools = [
        step.tool
        for step
        in result.plan.steps
    ]

    assert (
        tools
        == [
            "query_metadata",
            "sort_table",
        ]
    )

    page_counts = [
        int(
            row["页数"]
            .replace(
                "页",
                "",
            )
            .strip()
        )
        for row
        in (
            result
            .final_answer
            .table_rows
        )
    ]

    assert (
        page_counts
        == sorted(
            page_counts,
            reverse=True,
        )
    )