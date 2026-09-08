from typing import Any

from app.agent.plan_schemas import (
    AgentPlan,
)

from app.tools.registry import (
    get_tool,
)

from app.agent.plan_validator import (
    validate_plan,
)

def execute_plan(
    plan: AgentPlan,
) -> dict[str, Any]:
    """
    顺序执行 AgentPlan。

    支持：
    step_1 -> step_2 -> step_3

    如果 arguments 中存在 input_step，
    自动把对应上一步 ToolResult
    注入当前工具。
    """
    # ========================================================
    # Plan Validation
    # ========================================================

    validate_plan(
        plan
    )

    step_results = {}

    for step in plan.steps:

        print()
        print(
            f"执行 {step.step_id}: "
            f"{step.tool}"
        )

        print(
            f"说明："
            f"{step.description}"
        )

        tool = get_tool(
            step.tool
        )

        arguments = dict(
            step.arguments
        )

        # ====================================================
        # 处理上一步输入
        # ====================================================

        input_step = arguments.pop(
            "input_step",
            None,
        )

        if input_step is not None:

            if (
                input_step
                not in step_results
            ):
                raise ValueError(
                    f"{step.step_id} 引用了"
                    f"不存在的步骤："
                    f"{input_step}"
                )

            arguments[
                "input_table"
            ] = step_results[
                input_step
            ]

        # ====================================================
        # 调用真正的 Python Tool
        # ====================================================

        result = tool(
            **arguments
        )

        step_results[
            step.step_id
        ] = result

    return {
        "plan": plan,
        "step_results": step_results,
    }