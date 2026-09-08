from typing import Literal

from pydantic import BaseModel

from app.agent.final_answer_schemas import (
    FinalAnswer,
)

from app.agent.plan_schemas import (
    AgentPlan,
)

from app.tools.schemas import (
    TextResult,
)


class AgentRunResult(BaseModel):
    """
    Agent Runtime 的统一输出协议。

    result_type:
        structured
            结构化 ToolResult 流程

        grounded_text
            RAG / grounded text 流程

    markdown:
        当前 CLI 可以直接打印的最终结果。

    final_answer:
        structured 流程的结构化结果。

    text_result:
        grounded_text 流程的原始 grounded 结果。
    """

    result_type: Literal[
        "structured",
        "grounded_text",
    ]

    plan: AgentPlan

    markdown: str

    final_answer: (
        FinalAnswer
        | None
    ) = None

    text_result: (
        TextResult
        | None
    ) = None