from typing import Any

from app.agent.answer_schemas import (
    AnswerColumn,
    AnswerContext,
    AnswerOperation,
)

from app.agent.plan_schemas import (
    AgentPlan,
)

from app.tools.schemas import (
    ToolResult,
)


def get_final_tool_result(
    plan: AgentPlan,
    step_results: dict[
        str,
        Any,
    ],
) -> ToolResult:
    """
    获取执行链最后一步 ToolResult。
    """

    if not plan.steps:

        raise ValueError(
            "AgentPlan 中没有步骤。"
        )

    last_step_id = (
        plan.steps[-1].step_id
    )

    if (
        last_step_id
        not in step_results
    ):

        raise ValueError(
            f"缺少步骤结果："
            f"{last_step_id}"
        )

    result = step_results[
        last_step_id
    ]

    if not isinstance(
        result,
        ToolResult,
    ):

        raise TypeError(
            "当前 Answer Context Builder "
            "只支持 ToolResult，"
            f"实际类型为："
            f"{type(result).__name__}"
        )

    return result


def build_operations(
    plan: AgentPlan,
) -> list[AnswerOperation]:
    """
    把 Planner 执行计划转换成
    Answer Writer 可以理解的操作历史。

    注意：
    不执行任何计算，
    只描述已经发生过的操作。
    """

    operations = []

    for step in plan.steps:

        operations.append(
            AnswerOperation(
                step_id=step.step_id,

                tool=step.tool,

                description=(
                    step.description
                ),

                arguments=dict(
                    step.arguments
                ),
            )
        )

    return operations


def build_columns(
    result: ToolResult,
) -> list[AnswerColumn]:
    """
    把 ToolResult.column_specs
    转换成 Answer Context 的列语义。
    """

    columns = []

    for spec in result.column_specs:

        columns.append(
            AnswerColumn(
                field=spec.field,

                label=spec.label,

                role=spec.role,

                visible=spec.visible,

                format_hint=(
                    spec.format_hint
                ),

                unit=spec.unit,

                unit_field=(
                    spec.unit_field
                ),
            )
        )

    return columns


def build_rows(
    result: ToolResult,
) -> list[dict[str, Any]]:
    """
    复制最终 ToolResult rows。

    不做：
    - 排序
    - 聚合
    - 单位转换
    - 数值修改
    - 字段重命名

    Answer Context 必须忠实保存
    Executor 已经确定的结果。
    """

    return [
        dict(row)
        for row in result.rows
    ]


def build_answer_context(
    execution: dict[str, Any],
    user_question: str | None = None,
) -> AnswerContext:
    """
    Generic Answer Context Builder。

    这是 Executor 和未来 LLM Answer Writer
    之间的唯一接口。

    这里不应该出现：

    if metric == ...
    if source == "facts"
    if field == "page_count"

    它只处理通用数据协议。
    """

    plan = execution.get(
        "plan"
    )

    step_results = execution.get(
        "step_results"
    )

    if not isinstance(
        plan,
        AgentPlan,
    ):

        raise ValueError(
            "execution 中缺少有效的 AgentPlan。"
        )

    if not isinstance(
        step_results,
        dict,
    ):

        raise ValueError(
            "execution 中缺少 step_results。"
        )

    final_result = (
        get_final_tool_result(
            plan=plan,
            step_results=step_results,
        )
    )

    if user_question is None:

        user_question = (
            plan.user_goal
        )

    return AnswerContext(
        user_question=(
            user_question
        ),

        user_goal=(
            plan.user_goal
        ),

        answer_mode=(
            plan.answer_mode
        ),

        operations=(
            build_operations(
                plan
            )
        ),

        columns=(
            build_columns(
                final_result
            )
        ),

        rows=(
            build_rows(
                final_result
            )
        ),

        metadata=dict(
            final_result.metadata
        ),

        plot_path=(
            final_result.metadata.get(
                "plot_path"
            )
        ),
    )