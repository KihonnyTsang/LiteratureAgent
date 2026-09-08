import pytest

from app.agent.planner import (
    create_plan,
)


@pytest.mark.llm
@pytest.mark.parametrize(
    (
        "question",
        "expected_tools",
    ),
    [
        (
            "哪篇论文的功率密度最高？",
            [
                "query_facts",
                "aggregate_table",
                "sort_table",
            ],
        ),
        (
            "比较所有论文的功率密度并画图",
            [
                "query_facts",
                "aggregate_table",
                "sort_table",
                "plot_table",
            ],
        ),
        (
            "总结所有论文中出现过的 d33，包括引用数据",
            [
                "query_facts",
            ],
        ),
    ],
)
def test_planner_tool_selection(
    question: str,
    expected_tools: list[str],
) -> None:
    """
    使用真实 LLM 验证 Planner 的核心工具选择。

    不要求：

    - description 完全一致
    - user_goal 完全一致
    - metric 自然语言字符串完全一致

    只锁定真正影响 Agent 行为的
    Tool Pipeline。
    """

    plan = create_plan(
        question
    )

    actual_tools = [
        step.tool
        for step
        in plan.steps
    ]

    assert (
        actual_tools
        == expected_tools
    )


@pytest.mark.llm
def test_planner_all_mentions_scope() -> None:
    """
    用户明确要求包括引用数据时，
    query_facts 必须使用 all_mentions。
    """

    plan = create_plan(
        "总结所有论文中出现过的 d33，"
        "包括引用数据"
    )

    query_step = next(
        step
        for step
        in plan.steps
        if step.tool
        == "query_facts"
    )

    assert (
        query_step.arguments.get(
            "provenance_scope"
        )
        == "all_mentions"
    )