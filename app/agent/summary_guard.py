import math
import re
from typing import Any

from app.agent.answer_schemas import (
    AnswerContext,
)


# ============================================================
# 普通数字
# ============================================================

NUMBER_PATTERN = re.compile(
    r"(?<![\w.])"
    r"[-+]?"
    r"(?:"
    r"\d+(?:\.\d+)?"
    r"|"
    r"\.\d+"
    r")"
    r"(?:[eE][-+]?\d+)?"
)


# ============================================================
# Markdown / 文本列表序号
#
# 例如：
#
# 1. Siddiqui
# 2. Si
#
# 这些数字只是展示结构，
# 不是科研数据。
# ============================================================

LIST_INDEX_PATTERN = re.compile(
    r"(?m)^\s*\d+\s*[.)、]\s+"
)


def strip_list_indices(
    text: str,
) -> str:
    """
    在数值完整性检查之前，
    删除纯粹用于列表编号的数字。

    例如：

    1. A
    2. B

    不把 1 / 2 当作数据。
    """

    return LIST_INDEX_PATTERN.sub(
        "",
        text,
    )


def extract_numbers_from_text(
    text: str,
) -> list[float]:
    """
    从文本中提取数值。

    返回 float，
    后续使用严格数值近似比较，
    而不是字符串完全相等。
    """

    clean_text = strip_list_indices(
        text
    )

    numbers = []

    for match in NUMBER_PATTERN.findall(
        clean_text
    ):

        try:

            value = float(
                match
            )

        except ValueError:

            continue

        if math.isfinite(
            value
        ):

            numbers.append(
                value
            )

    return numbers


def collect_numbers(
    value: Any,
    output: list[float],
) -> None:
    """
    递归收集 AnswerContext 中已经存在的数字。

    不做任何数学运算。
    """

    if value is None:
        return

    # bool 是 int 的子类，
    # 不能当作数字数据。
    if isinstance(
        value,
        bool,
    ):
        return

    if isinstance(
        value,
        (int, float),
    ):

        numeric_value = float(
            value
        )

        if math.isfinite(
            numeric_value
        ):

            output.append(
                numeric_value
            )

        return

    if isinstance(
        value,
        str,
    ):

        output.extend(
            extract_numbers_from_text(
                value
            )
        )

        return

    if isinstance(
        value,
        dict,
    ):

        for item in value.values():

            collect_numbers(
                item,
                output,
            )

        return

    if isinstance(
        value,
        (list, tuple, set),
    ):

        for item in value:

            collect_numbers(
                item,
                output,
            )


def get_allowed_numbers(
    context: AnswerContext,
) -> list[float]:
    """
    Answer Writer 被允许使用的所有数字。

    包括：

    1. AnswerContext 中已有数字
    2. WriterContext 明确暴露的 row_count
    """

    allowed_numbers = []

    collect_numbers(
        context.model_dump(),
        allowed_numbers,
    )

    # WriterContext 会明确暴露 row_count，
    # 因此 Guard 也必须允许该数字。
    allowed_numbers.append(
        float(
            len(context.rows)
        )
    )

    return allowed_numbers


def numbers_match(
    generated_value: float,
    allowed_value: float,
) -> bool:
    """
    判断两个数字是否表示同一个确定性结果。

    允许：

    0.41020000000000006
    ->
    0.4102

    0.10099999999999999
    ->
    0.101

    但不允许：

    0.4102
    ->
    0.410

    使用非常严格的浮点容差，
    只消除 binary floating-point noise。
    """

    return math.isclose(
        generated_value,
        allowed_value,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )


def number_is_allowed(
    number: float,
    allowed_numbers: list[float],
) -> bool:
    """
    检查 Summary 中的一个数字
    是否已经存在于 AnswerContext。
    """

    return any(
        numbers_match(
            number,
            allowed_number,
        )
        for allowed_number
        in allowed_numbers
    )


def format_guard_number(
    value: float,
) -> str:
    """
    用于 Guard 日志显示。

    不影响实际数据。
    """

    return f"{value:.12g}"


def find_unsupported_numbers(
    summary: str,
    context: AnswerContext,
) -> list[str]:
    """
    找出 LLM 自己创造的数字。
    """

    allowed_numbers = (
        get_allowed_numbers(
            context
        )
    )

    summary_numbers = (
        extract_numbers_from_text(
            summary
        )
    )

    unsupported = []

    for number in summary_numbers:

        if number_is_allowed(
            number,
            allowed_numbers,
        ):
            continue

        displayed = (
            format_guard_number(
                number
            )
        )

        if displayed not in unsupported:

            unsupported.append(
                displayed
            )

    return unsupported


def validate_summary(
    summary: str,
    context: AnswerContext,
) -> tuple[
    bool,
    list[str],
]:
    """
    Summary 数值完整性检查。

    只允许：
    - AnswerContext 中已有数字
    - 消除了浮点噪声后的等价表示

    不允许：
    - 新百分比
    - 新倍数
    - 新平均值
    - 新范围边界
    - 明显舍入后的新数字
    """

    unsupported_numbers = (
        find_unsupported_numbers(
            summary=summary,
            context=context,
        )
    )

    return (
        len(
            unsupported_numbers
        ) == 0,
        unsupported_numbers,
    )