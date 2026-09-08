from app.tools.schemas import (
    ColumnSpec,
    ToolResult,
)

from app.tools.table_tool import (
    aggregate_table,
    sort_table,
)


def build_scientific_table() -> ToolResult:
    """
    构造具有科学语义的 ToolResult。
    """

    return ToolResult(
        columns=[
            "title",
            "value",
            "raw_value",
            "raw_unit",
            "evidence",
        ],

        rows=[
            {
                "title": "Paper A",
                "value": 82.2,
                "raw_value": 8.22,
                "raw_unit": "mW/cm²",
                "evidence": "Reported power density.",
            },
            {
                "title": "Paper B",
                "value": 135.0,
                "raw_value": 13.5,
                "raw_unit": "mW/cm²",
                "evidence": "Maximum output power density.",
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
                field="value",
                label="输出功率密度",
                role="measure",
                visible=True,
                format_hint="number",
                unit="W/m²",
            ),

            ColumnSpec(
                field="raw_value",
                label="原始输出功率密度",
                role="raw_measure",
                visible=True,
                format_hint="number",
                unit_field="raw_unit",
            ),

            ColumnSpec(
                field="raw_unit",
                label="原始单位",
                role="unit",
                visible=True,
                format_hint="text",
            ),

            ColumnSpec(
                field="evidence",
                label="证据",
                role="evidence",
                visible=False,
                format_hint="text",
            ),
        ],

        metadata={
            "metric": "synthetic_metric",
        },
    )


def test_semantic_schema() -> None:
    """
    验证 ColumnSpec 语义在确定性 Tool Pipeline 中保持。

    不测试任何具体业务代码分支。
    """

    input_table = (
        build_scientific_table()
    )

    # ========================================================
    # Initial semantic contract
    # ========================================================

    value_spec = (
        input_table.get_column_spec(
            "value"
        )
    )

    assert value_spec is not None

    assert (
        value_spec.role
        == "measure"
    )

    assert (
        value_spec.label
        == "输出功率密度"
    )

    assert (
        value_spec.unit
        == "W/m²"
    )

    raw_spec = (
        input_table.get_column_spec(
            "raw_value"
        )
    )

    assert raw_spec is not None

    assert (
        raw_spec.role
        == "raw_measure"
    )

    assert (
        raw_spec.unit_field
        == "raw_unit"
    )

    # ========================================================
    # Sort must preserve semantic schema
    # ========================================================

    sorted_result = sort_table(
        input_table=input_table,
        field="value",
        order="descending",
    )

    sorted_value_spec = (
        sorted_result.get_column_spec(
            "value"
        )
    )

    assert (
        sorted_value_spec
        is not None
    )

    assert (
        sorted_value_spec.role
        == "measure"
    )

    assert (
        sorted_value_spec.unit
        == "W/m²"
    )

    assert (
        sorted_result.rows[0][
            "title"
        ]
        == "Paper B"
    )

    # ========================================================
    # MAX must preserve complete source row + schema
    # ========================================================

    max_result = aggregate_table(
        input_table=input_table,
        operation="max",
        field="value",
    )

    assert (
        len(max_result.rows)
        == 1
    )

    assert (
        max_result.rows[0][
            "title"
        ]
        == "Paper B"
    )

    assert (
        max_result.rows[0][
            "raw_value"
        ]
        == 13.5
    )

    assert (
        max_result.rows[0][
            "evidence"
        ]
        == "Maximum output power density."
    )

    max_value_spec = (
        max_result.get_column_spec(
            "value"
        )
    )

    assert max_value_spec is not None

    assert (
        max_value_spec.unit
        == "W/m²"
    )

    # ========================================================
    # MEAN creates aggregate measure semantic
    # ========================================================

    mean_result = aggregate_table(
        input_table=input_table,
        operation="mean",
        field="value",
    )

    aggregate_spec = (
        mean_result.get_column_spec(
            "value"
        )
    )

    assert aggregate_spec is not None

    assert (
        aggregate_spec.role
        == "measure"
    )

    assert (
        aggregate_spec.label
        == "输出功率密度"
    )

    assert (
        aggregate_spec.unit
        == "W/m²"
    )