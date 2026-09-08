from typing import Any

from pydantic import (
    BaseModel,
    Field,
)


class FinalAnswer(BaseModel):
    """
    LiteratureAgent 最终输出。

    summary:
        LLM 负责的自然语言总结。

    table:
        Python 确定性生成。

    evidence:
        Python 确定性生成。

    plot_path:
        Executor 原始图表路径。

    warnings:
        根据数据语义确定性生成。
    """

    summary: str

    table_columns: list[str] = Field(
        default_factory=list
    )

    table_rows: list[
        dict[str, Any]
    ] = Field(
        default_factory=list
    )

    evidence_rows: list[
        dict[str, Any]
    ] = Field(
        default_factory=list
    )

    plot_path: str | None = None

    warnings: list[str] = Field(
        default_factory=list
    )