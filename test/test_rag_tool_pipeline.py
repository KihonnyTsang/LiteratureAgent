import pytest

from app.agent.executor import (
    execute_plan,
)

from app.agent.plan_schemas import (
    AgentPlan,
    ToolStep,
)

from app.tools.schemas import (
    TextResult,
)


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.slow
def test_rag_tool_pipeline() -> None:
    """
    验证：

        fixed AgentPlan
        → Executor
        → rag_search
        → TextResult

    这里故意不调用 Planner。

    Planner 已由 test_planner.py
    独立测试。

    本测试关注 RAG Tool Pipeline。
    """

    question = (
        "为什么加入 BaTiO3 后"
        "压电输出会增强？"
    )

    plan = AgentPlan(
        user_goal=(
            "基于文献解释 BaTiO3 "
            "增强压电输出的机制"
        ),

        steps=[
            ToolStep(
                step_id="step_1",

                tool="rag_search",

                arguments={
                    "question":
                        question,

                    "top_k":
                        5,
                },

                description=(
                    "检索相关文献并生成"
                    "有证据支撑的回答"
                ),
            ),
        ],

        answer_mode="text",
    )

    execution = execute_plan(
        plan
    )

    assert (
        "step_1"
        in execution["step_results"]
    )

    result = (
        execution[
            "step_results"
        ][
            "step_1"
        ]
    )

    assert isinstance(
        result,
        TextResult,
    )

    # ========================================================
    # Grounded Answer
    # ========================================================

    assert (
        result.text
        .strip()
    )

    # ========================================================
    # Sources
    # ========================================================

    assert result.sources

    for source in result.sources:

        assert source.source_id

        assert source.title

        assert (
            source.page_number
            is not None
        )

        assert (
            source.chunk_index
            is not None
        )

        assert source.filename

        assert (
            source.score
            is not None
        )

    # ========================================================
    # Metadata
    # ========================================================

    assert isinstance(
        result.metadata,
        dict,
    )