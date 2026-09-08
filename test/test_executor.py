import pytest

from app.agent.executor import (
    execute_plan,
)

from app.agent.plan_schemas import (
    AgentPlan,
    ToolStep,
)

from app.tools.schemas import (
    ToolResult,
)


@pytest.mark.integration
def test_executor_metadata_sort_pipeline() -> None:
    """
    使用固定计划验证 Executor。

    这里故意不调用 Planner / LLM。

    测试重点：

    1. ToolStep 顺序执行
    2. input_step 正确解析
    3. ToolResult 正确向下游传递
    4. sort_table 得到正确排序结果

    会读取真实本地 SQLite，
    因此属于 integration test。
    """

    plan = AgentPlan(
        user_goal=(
            "按页数从多到少"
            "排列所有论文"
        ),

        steps=[
            ToolStep(
                step_id="step_1",

                tool="query_metadata",

                arguments={
                    "fields": [
                        "title",
                        "page_count",
                    ],

                    "scope":
                        "all_documents",
                },

                description=(
                    "读取论文标题和页数"
                ),
            ),

            ToolStep(
                step_id="step_2",

                tool="sort_table",

                arguments={
                    "input_step":
                        "step_1",

                    "field":
                        "page_count",

                    "order":
                        "descending",
                },

                description=(
                    "按页数降序排列"
                ),
            ),
        ],

        answer_mode=(
            "text_and_table"
        ),
    )

    execution = execute_plan(
        plan
    )

    assert (
        set(
            execution[
                "step_results"
            ]
        )
        == {
            "step_1",
            "step_2",
        }
    )

    metadata_result = (
        execution[
            "step_results"
        ][
            "step_1"
        ]
    )

    sorted_result = (
        execution[
            "step_results"
        ][
            "step_2"
        ]
    )

    assert isinstance(
        metadata_result,
        ToolResult,
    )

    assert isinstance(
        sorted_result,
        ToolResult,
    )

    assert (
        metadata_result.rows
    )

    assert (
        sorted_result.rows
    )

    assert (
        len(
            sorted_result.rows
        )
        == len(
            metadata_result.rows
        )
    )

    page_counts = [
        row["page_count"]
        for row
        in sorted_result.rows
    ]

    assert (
        page_counts
        == sorted(
            page_counts,
            reverse=True,
        )
    )