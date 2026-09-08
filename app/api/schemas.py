from typing import Literal

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

from app.agent.runtime_schemas import (
    AgentRunResult,
)

class HealthResponse(BaseModel):
    """
    API 健康检查响应。
    """

    status: Literal["ok"]

    service: str

    version: str


class AgentRunRequest(BaseModel):
    """
    Agent API 请求。
    """

    question: str = Field(
        min_length=1,
        description="用户提交的科研文献问题。",
    )

    @field_validator(
        "question"
    )
    @classmethod
    def validate_question(
        cls,
        value: str,
    ) -> str:
        """
        清理并验证用户问题。
        """

        cleaned = value.strip()

        if not cleaned:

            raise ValueError(
                "question 不能为空。"
            )

        return cleaned

class AgentRunAPIResponse(
    AgentRunResult
):
    """
    FastAPI 对 AgentRunResult
    增加的 HTTP-specific 信息。

    Agent Runtime 本身仍然只负责
    本地 plot_path。

    API Layer 再把它映射为
    浏览器可访问的 plot_url。
    """

    plot_url: str | None = Field(
        default=None,
        description=(
            "如果本次 Agent 生成图表，"
            "这里提供对应的 HTTP URL。"
        ),
    )