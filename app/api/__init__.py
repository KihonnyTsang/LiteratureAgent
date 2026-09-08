from typing import Literal

from pydantic import (
    BaseModel,
    Field,
    field_validator,
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