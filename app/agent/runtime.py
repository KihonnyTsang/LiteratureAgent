from typing import Any

from app.agent.answer_context import (
    build_answer_context,
)

from app.agent.answer_renderer import (
    render_final_answer,
    render_final_answer_markdown,
)

from app.agent.answer_writer import (
    write_summary,
)

from app.agent.executor import (
    execute_plan,
)

from app.agent.planner import (
    create_plan,
)

from app.agent.runtime_schemas import (
    AgentRunResult,
)

from app.agent.text_result_renderer import (
    render_text_result_markdown,
)

from app.tools.schemas import (
    TextResult,
    ToolResult,
)


def get_final_execution_result(
    execution: dict[str, Any],
) -> (
    ToolResult
    | TextResult
):
    """
    获取 Executor 最后一步产生的结果。
    """

    plan = execution.get(
        "plan"
    )

    step_results = execution.get(
        "step_results"
    )

    if plan is None:

        raise ValueError(
            "execution 中缺少 plan。"
        )

    if not isinstance(
        step_results,
        dict,
    ):

        raise ValueError(
            "execution 中缺少 step_results。"
        )

    if not plan.steps:

        raise ValueError(
            "AgentPlan 中没有执行步骤。"
        )

    last_step_id = (
        plan.steps[-1].step_id
    )

    if (
        last_step_id
        not in step_results
    ):

        raise ValueError(
            f"缺少最终步骤结果："
            f"{last_step_id}"
        )

    result = step_results[
        last_step_id
    ]

    if not isinstance(
        result,
        (
            ToolResult,
            TextResult,
        ),
    ):

        raise TypeError(
            "Agent Runtime 不支持"
            "当前工具结果类型："
            f"{type(result).__name__}"
        )

    return result


def run_agent(
    question: str,
) -> AgentRunResult:
    """
    LiteratureAgent 的统一 Runtime 入口。

    流程：

    User Question
        ↓
    Planner
        ↓
    Executor
        ↓
    Result Protocol Dispatch

    TextResult:
        grounded text
        → deterministic source renderer

    ToolResult:
        AnswerContext
        → LLM Summary
        → Summary Guard
        → deterministic renderer
    """

    question = (
        question.strip()
    )

    if not question:

        raise ValueError(
            "question 不能为空。"
        )

    # ========================================================
    # 1. Planner
    # ========================================================

    plan = create_plan(
        question
    )

    # ========================================================
    # 2. Executor
    # ========================================================

    execution = execute_plan(
        plan
    )

    # ========================================================
    # 3. Final tool result
    # ========================================================

    result = (
        get_final_execution_result(
            execution
        )
    )

    # ========================================================
    # 4. Grounded Text branch
    # ========================================================

    if isinstance(
        result,
        TextResult,
    ):

        markdown = (
            render_text_result_markdown(
                result
            )
        )

        return AgentRunResult(
            result_type=(
                "grounded_text"
            ),

            plan=plan,

            markdown=markdown,

            text_result=result,
        )

    # ========================================================
    # 5. Structured branch
    # ========================================================

    if isinstance(
        result,
        ToolResult,
    ):

        context = (
            build_answer_context(
                execution=execution,
                user_question=question,
            )
        )

        summary = write_summary(
            context
        )

        final_answer = (
            render_final_answer(
                context=context,
                summary=summary,
            )
        )

        markdown = (
            render_final_answer_markdown(
                final_answer
            )
        )

        return AgentRunResult(
            result_type=(
                "structured"
            ),

            plan=plan,

            markdown=markdown,

            final_answer=(
                final_answer
            ),
        )

    # 理论上前面的类型检查
    # 已经保证不会走到这里。
    raise RuntimeError(
        "未知 Runtime 状态。"
    )