from app.tools.schemas import (
    ColumnSpec,
    ToolResult,
)

from app.tools.table_tool import (
    sort_table,
)


def test_table_pipeline() -> None:
    """
    验证通用 sort_table：

    - descending 排序
    - None 始终放在最后
    - rows 不丢失
    - ColumnSpec 保持
    - metadata 正确记录排序语义
    """

    input_table = ToolResult(
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
                "page_count": None,
            },
            {
                "title": "Paper C",
                "page_count": 30,
            },
            {
                "title": "Paper D",
                "page_count": 20,
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
                format_hint="integer",
            ),
        ],

        metadata={
            "source": "synthetic_test",
        },
    )

    result = sort_table(
        input_table=input_table,
        field="page_count",
        order="descending",
    )

    assert [
        row["title"]
        for row
        in result.rows
    ] == [
        "Paper C",
        "Paper D",
        "Paper A",
        "Paper B",
    ]

    assert [
        row["page_count"]
        for row
        in result.rows
    ] == [
        30,
        20,
        10,
        None,
    ]

    assert (
        len(result.rows)
        == len(input_table.rows)
    )

    assert (
        result.metadata[
            "sorted_by"
        ]
        == "page_count"
    )

    assert (
        result.metadata[
            "sort_order"
        ]
        == "descending"
    )

    assert (
        result.metadata[
            "source"
        ]
        == "synthetic_test"
    )

    page_spec = (
        result.get_column_spec(
            "page_count"
        )
    )

    assert page_spec is not None

    assert (
        page_spec.label
        == "页数"
    )

    assert (
        page_spec.role
        == "measure"
    )