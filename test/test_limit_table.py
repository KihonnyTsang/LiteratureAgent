import pytest

from app.tools.schemas import (
    ColumnSpec,
    ToolResult,
)

from app.tools.table_tool import (
    limit_table,
)


def make_table() -> ToolResult:

    return ToolResult(
        columns=[
            "title",
            "value",
        ],

        rows=[
            {
                "title": "Paper A",
                "value": 30.0,
            },
            {
                "title": "Paper B",
                "value": 20.0,
            },
            {
                "title": "Paper C",
                "value": 10.0,
            },
        ],

        column_specs=[
            ColumnSpec(
                field="title",
                label="论文",
                role="dimension",
                visible=True,
                format_hint="text",
            ),
            ColumnSpec(
                field="value",
                label="数值",
                role="measure",
                visible=True,
                format_hint="number",
                unit="W",
            ),
        ],

        metadata={
            "source": "test",
            "sorted_by": "value",
            "sort_order": "descending",
        },
    )


def test_limit_table_keeps_first_n_rows():

    input_table = make_table()

    result = limit_table(
        input_table=input_table,
        limit=2,
    )

    assert [
        row["title"]
        for row in result.rows
    ] == [
        "Paper A",
        "Paper B",
    ]

    assert result.metadata[
        "source"
    ] == "test"

    assert result.metadata[
        "sorted_by"
    ] == "value"

    assert result.metadata[
        "sort_order"
    ] == "descending"

    assert result.metadata[
        "limit"
    ] == 2

    assert result.metadata[
        "pre_limit_row_count"
    ] == 3

    assert result.metadata[
        "post_limit_row_count"
    ] == 2

    assert result.metadata[
        "truncated"
    ] is True

    assert result.column_specs == (
        input_table.column_specs
    )

    assert (
        result.column_specs[0]
        is not input_table.column_specs[0]
    )


def test_limit_table_returns_all_when_limit_exceeds_rows():

    result = limit_table(
        input_table=make_table(),
        limit=10,
    )

    assert len(result.rows) == 3

    assert result.metadata[
        "pre_limit_row_count"
    ] == 3

    assert result.metadata[
        "post_limit_row_count"
    ] == 3

    assert result.metadata[
        "truncated"
    ] is False


@pytest.mark.parametrize(
    "limit",
    [
        0,
        -1,
    ],
)
def test_limit_table_rejects_non_positive_limit(
    limit: int,
):

    with pytest.raises(
        ValueError,
        match="limit 必须大于 0",
    ):
        limit_table(
            input_table=make_table(),
            limit=limit,
        )


@pytest.mark.parametrize(
    "limit",
    [
        1.5,
        "10",
        True,
    ],
)
def test_limit_table_rejects_non_integer_limit(
    limit,
):

    with pytest.raises(
        TypeError,
        match="limit 必须是整数",
    ):
        limit_table(
            input_table=make_table(),
            limit=limit,
        )
