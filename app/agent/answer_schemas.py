from typing import Any

from pydantic import (
    BaseModel,
    Field,
)


class AnswerOperation(BaseModel):
    """
    告诉 Answer Writer：

    Agent 实际执行过什么操作。

    例如：
    query_facts
    aggregate_table
    sort_table
    plot_table
    """

    step_id: str

    tool: str

    description: str | None = None

    arguments: dict[
        str,
        Any,
    ] = Field(
        default_factory=dict
    )


class AnswerColumn(BaseModel):
    """
    最终结果中某一列的语义。

    Answer Writer 不需要知道：

    - 功率密度
    - d33
    - page_count
    - voltage

    它只读取：

    field
    label
    role
    unit
    等语义。
    """

    field: str

    label: str

    role: str

    visible: bool = True

    format_hint: str | None = None

    unit: str | None = None

    unit_field: str | None = None


class AnswerContext(BaseModel):
    """
    Executor 与最终 Answer Writer 之间的
    标准数据协议。
    """

    user_question: str

    user_goal: str

    answer_mode: str

    operations: list[
        AnswerOperation
    ] = Field(
        default_factory=list
    )

    columns: list[
        AnswerColumn
    ] = Field(
        default_factory=list
    )

    rows: list[
        dict[str, Any]
    ] = Field(
        default_factory=list
    )

    metadata: dict[
        str,
        Any,
    ] = Field(
        default_factory=dict
    )

    plot_path: str | None = None