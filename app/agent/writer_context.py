from typing import Any

from pydantic import (
    BaseModel,
    Field,
)

from app.agent.answer_schemas import (
    AnswerContext,
)


class WriterContext(BaseModel):
    """
    专门提供给 LLM Summary Writer 的
    最小安全上下文。

    注意：

    Deterministic Renderer 仍然使用完整
    AnswerContext。

    WriterContext 只暴露生成自然语言总结
    真正需要的信息。
    """

    user_question: str

    user_goal: str

    answer_mode: str

    operation_descriptions: list[str] = Field(
        default_factory=list
    )

    row_count: int

    headline_rows: list[
        dict[str, Any]
    ] = Field(
        default_factory=list
    )

    warnings: list[str] = Field(
        default_factory=list
    )

    plot_generated: bool = False


def get_visible_fields(
    context: AnswerContext,
) -> list[str]:
    """
    获取允许面向用户展示的字段。
    """

    return [
        column.field
        for column in context.columns
        if column.visible
    ]


def build_headline_rows(
    context: AnswerContext,
    max_rows: int = 1,
) -> list[dict[str, Any]]:
    """
    给 Summary Writer 少量 headline rows。

    默认只给最终结果第一行。

    这样对于已经排序的结果，
    LLM 可以说明排名第一的对象，
    但不能根据完整结果自行重新分析分布、
    范围或趋势。
    """

    visible_fields = (
        get_visible_fields(
            context
        )
    )

    headline_rows = []

    for row in context.rows[
        :max_rows
    ]:

        headline_row = {}

        for field in visible_fields:

            if field not in row:
                continue

            value = row[
                field
            ]

            if value is None:
                continue

            headline_row[
                field
            ] = value

        headline_rows.append(
            headline_row
        )

    return headline_rows


def build_writer_context(
    context: AnswerContext,
) -> WriterContext:
    """
    从完整 AnswerContext 构造
    最小化 WriterContext。

    这里没有 metric / source / page_count
    等业务特判。
    """

    operation_descriptions = []

    for operation in (
        context.operations
    ):

        if operation.description:

            operation_descriptions.append(
                operation.description
            )

        else:

            operation_descriptions.append(
                operation.tool
            )

    return WriterContext(
        user_question=(
            context.user_question
        ),

        user_goal=(
            context.user_goal
        ),

        answer_mode=(
            context.answer_mode
        ),

        operation_descriptions=(
            operation_descriptions
        ),

        row_count=len(
            context.rows
        ),

        headline_rows=(
            build_headline_rows(
                context=context,
                max_rows=1,
            )
        ),

        warnings=[],

        plot_generated=(
            context.plot_path
            is not None
        ),
    )