from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolStep(BaseModel):
    """
    Agent 计划中的一个工具调用步骤。

    arguments 保持通用 dict，
    不把 page_count、power_density 等具体问题
    写死在顶层 Schema 中。
    """

    step_id: str

    tool: Literal[
        "rag_search",
        "query_facts",
        "query_metadata",
        "filter_table",
        "aggregate_table",
        "sort_table",
        "limit_table",
        "plot_table",
    ]

    arguments: dict[str, Any] = Field(
        default_factory=dict
    )

    description: str | None = None


class AgentPlan(BaseModel):
    """
    DeepSeek Planner 输出的完整执行计划。
    """

    user_goal: str

    steps: list[ToolStep]

    answer_mode: Literal[
        "text",
        "table",
        "text_and_table",
        "text_and_plot",
        "text_table_and_plot",
    ] = "text"