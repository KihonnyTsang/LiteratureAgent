from app.tools.schemas import (
    ColumnSpec,
    ToolResult,
)

from app.tools.table_tool import (
    aggregate_table,
)


def build_page_table() -> ToolResult:
    """
    构造完全确定性的论文页数测试表。

    不依赖：

    - LLM
    - SQLite
    - Qdrant
    - Embedding
    """

    return ToolResult(
        columns=[
            "title",
            "page_count",
        ],

        rows=[
            {
                "title": "Paper A",
                "page_count": 10,
            },
            {
                "title": "Paper B",
                "page_count": 20,
            },
            {
                "title": "Paper C",
                "page_count": 30,
            },
        ],

        column_specs=[
            ColumnSpec(
                field="title",
                label="论文",
                role="identifier",
                visible=True,
                format_hint="text",
            ),
            ColumnSpec(
                field="page_count",
                label="页数",
                role="measure",
                visible=True,
                format_hint="number",
            ),
        ],

        metadata={
            "source": "synthetic_test",
        },
    )


def test_aggregate_pipeline() -> None:
    """
    验证确定性 aggregation。

    mean:
        (10 + 20 + 30) / 3 = 20

    sum:
        10 + 20 + 30 = 60
    """

    input_table = build_page_table()

    # ========================================================
    # Mean
    # ========================================================

    mean_result = aggregate_table(
        input_table=input_table,
        operation="mean",
        field="page_count",
    )

    assert (
        mean_result.columns
        == ["value"]
    )

    assert (
        mean_result.rows
        == [
            {
                "value": 20,
            }
        ]
    )

    assert (
        mean_result.metadata[
            "aggregation"
        ]
        == "mean"
    )

    assert (
        mean_result.metadata[
            "aggregation_field"
        ]
        == "page_count"
    )

    assert (
        mean_result.metadata[
            "source"
        ]
        == "synthetic_test"
    )

    mean_spec = (
        mean_result.get_column_spec(
            "value"
        )
    )

    assert mean_spec is not None

    assert (
        mean_spec.label
        == "页数"
    )

    assert (
        mean_spec.role
        == "measure"
    )

    # ========================================================
    # Sum
    # ========================================================

    sum_result = aggregate_table(
        input_table=input_table,
        operation="sum",
        field="page_count",
    )

    assert (
        sum_result.rows
        == [
            {
                "value": 60,
            }
        ]
    )

    assert (
        sum_result.metadata[
            "aggregation"
        ]
        == "sum"
    )