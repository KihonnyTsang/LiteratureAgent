from app.agent.answer_context import (
    build_answer_context,
)

from app.agent.plan_schemas import (
    AgentPlan,
    ToolStep,
)

from app.tools.schemas import (
    ColumnSpec,
    ToolResult,
)


def test_answer_context() -> None:
    """
    验证 AnswerContext Builder。

    使用：

        Fixed AgentPlan
        +
        Fixed ToolResult

    不执行：

        Planner
        Executor
        LLM
        SQLite
        Qdrant
    """

    question = (
        "比较所有论文的功率密度，"
        "按从高到低排序，并绘制图表"
    )

    # ========================================================
    # Fixed Plan
    # ========================================================

    plan = AgentPlan(
        user_goal=(
            "比较论文功率密度并绘图"
        ),

        steps=[
            ToolStep(
                step_id="step_1",
                tool="query_facts",
                arguments={
                    "metric":
                        "power_density",
                    "scope":
                        "all_documents",
                    "provenance_scope":
                        "author_results",
                },
                description=(
                    "查询结构化事实"
                ),
            ),

            ToolStep(
                step_id="step_2",
                tool="aggregate_table",
                arguments={
                    "input_step":
                        "step_1",
                    "operation":
                        "max",
                    "field":
                        "value",
                    "group_by":
                        "document_id",
                },
                description=(
                    "每篇论文取最大值"
                ),
            ),

            ToolStep(
                step_id="step_3",
                tool="sort_table",
                arguments={
                    "input_step":
                        "step_2",
                    "field":
                        "value",
                    "order":
                        "descending",
                },
                description=(
                    "按数值降序排序"
                ),
            ),

            ToolStep(
                step_id="step_4",
                tool="plot_table",
                arguments={
                    "input_step":
                        "step_3",
                    "chart_type":
                        "bar",
                    "x":
                        "title",
                    "y":
                        "value",
                    "title":
                        "功率密度比较",
                },
                description=(
                    "绘制比较图"
                ),
            ),
        ],

        answer_mode=(
            "text_table_and_plot"
        ),
    )

    # ========================================================
    # Fixed final ToolResult
    # ========================================================

    final_result = ToolResult(
        columns=[
            "title",
            "value",
            "unit",
        ],

        rows=[
            {
                "title": "Paper B",
                "value": 135.0,
                "unit": "W/m²",
            },
            {
                "title": "Paper A",
                "value": 82.2,
                "unit": "W/m²",
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
                field="unit",
                label="单位",
                role="unit",
                visible=False,
                format_hint="text",
            ),
        ],

        metadata={
            "plot_path":
                "/tmp/power_density_test.png",

            "chart_type":
                "bar",

            "sorted_by":
                "value",
        },
    )

    execution = {
        "plan": plan,

        "step_results": {
            "step_4":
                final_result,
        },
    }

    # ========================================================
    # Build AnswerContext
    # ========================================================

    context = build_answer_context(
        execution=execution,
        user_question=question,
    )

    # ========================================================
    # Core fields
    # ========================================================

    assert (
        context.user_question
        == question
    )

    assert (
        context.user_goal
        == "比较论文功率密度并绘图"
    )

    assert (
        context.answer_mode
        == "text_table_and_plot"
    )

    # ========================================================
    # Operations
    # ========================================================

    assert [
        operation.tool
        for operation
        in context.operations
    ] == [
        "query_facts",
        "aggregate_table",
        "sort_table",
        "plot_table",
    ]

    assert (
        context.operations[2]
        .arguments[
            "order"
        ]
        == "descending"
    )

    # ========================================================
    # Columns
    # ========================================================

    assert [
        column.field
        for column
        in context.columns
    ] == [
        "title",
        "value",
        "unit",
    ]

    value_column = next(
        column
        for column
        in context.columns
        if column.field
        == "value"
    )

    assert (
        value_column.label
        == "输出功率密度"
    )

    assert (
        value_column.role
        == "measure"
    )

    assert (
        value_column.unit
        == "W/m²"
    )

    # ========================================================
    # Rows
    # ========================================================

    assert (
        context.rows
        == final_result.rows
    )

    assert (
        context.rows
        is not final_result.rows
    )

    assert (
        context.rows[0]
        is not final_result.rows[0]
    )

    # ========================================================
    # Metadata / Plot
    # ========================================================

    assert (
        context.metadata[
            "chart_type"
        ]
        == "bar"
    )

    assert (
        context.plot_path
        == "/tmp/power_density_test.png"
    )