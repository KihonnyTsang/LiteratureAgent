from app.agent.answer_prompt import (
    ANSWER_SYSTEM_PROMPT,
    build_answer_prompt,
)

from app.agent.answer_schemas import (
    AnswerContext,
)

from app.agent.summary_guard import (
    validate_summary,
)

from app.llm.siliconflow_client import (
    chat,
)

from app.agent.writer_context import (
    build_writer_context,
)

MAX_REWRITE_ATTEMPTS = 1


def call_answer_writer(
    user_prompt: str,
) -> str:
    """
    调用 LLM 生成 Summary。
    """

    messages = [
        {
            "role": "system",
            "content":
                ANSWER_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content":
                user_prompt,
        },
    ]

    result = chat(
        messages=messages,
        temperature=0.0,
    )

    if not result:

        raise RuntimeError(
            "Answer Writer 没有返回内容。"
        )

    return result.strip()


def write_summary(
    context: AnswerContext,
) -> str:
    """
    LLM 只负责自然语言 Summary。

    Summary 必须通过数值完整性检查。

    如果 LLM 引入 AnswerContext 中
    不存在的新数字：

    1. 自动要求重写一次
    2. 再失败则使用安全 fallback

    从而保证错误的派生数值
    不进入最终答案。
    """
    # ========================================================
    # Empty structured result
    # ========================================================

    if not context.rows:

        return (
            "当前结构化查询结果为空，"
            "未发现符合本次查询条件的数据。"
        )

    writer_context = (
        build_writer_context(
            context
        )
    )

    base_prompt = build_answer_prompt(
        writer_context
    )

    summary = call_answer_writer(
        base_prompt
    )

    # ========================================================
    # 第一次完整性检查
    # ========================================================

    (
        is_valid,
        unsupported_numbers,
    ) = validate_summary(
        summary=summary,
        context=context,
    )

    if is_valid:
        return summary

    print()
    print(
        "Answer Guard："
        "检测到 LLM 产生了 "
        "AnswerContext 中不存在的数字：",
        unsupported_numbers,
    )

    # ========================================================
    # 自动重写
    # ========================================================

    rewrite_prompt = (
        base_prompt
        + "\n\n"
        + "你上一次生成的总结没有通过"
        "数值完整性检查。\n"
        + "发现以下 AnswerContext 中不存在的数字：\n"
        + str(
            unsupported_numbers
        )
        + "\n\n"
        + "请重新生成总结。\n"
        + "严格要求：\n"
        + "- 不得计算百分比差异。\n"
        + "- 不得计算倍数。\n"
        + "- 不得创建新的范围。\n"
        + "- 不得对数值重新舍入。\n"
        + "- 所有出现的数字必须逐值来自 "
          "AnswerContext。\n"
        + "- 只输出简洁的自然语言总结，"
          "不要输出表格、证据列表或文件路径。\n"
    )

    for _ in range(
        MAX_REWRITE_ATTEMPTS
    ):

        rewritten = call_answer_writer(
            rewrite_prompt
        )

        (
            is_valid,
            unsupported_numbers,
        ) = validate_summary(
            summary=rewritten,
            context=context,
        )

        if is_valid:

            print(
                "Answer Guard："
                "重写后的 Summary "
                "已通过数值完整性检查。"
            )

            return rewritten

    # ========================================================
    # Fail-safe
    # ========================================================

    print(
        "Answer Guard："
        "重写后仍未通过检查，"
        "使用安全 Summary。"
    )

    return (
        "已完成所请求的文献数据分析。"
        "确定性的比较结果、原始数据、"
        "证据和图表见下方。"
    )