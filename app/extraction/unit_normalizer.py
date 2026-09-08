import re

from dataclasses import dataclass

from pint import UnitRegistry
from pint.errors import (
    DimensionalityError,
    UndefinedUnitError,
)

from app.extraction.schemas import (
    ExtractedFact,
    MetricSpec,
)


ureg = UnitRegistry(
    autoconvert_offset_to_baseunit=True
)


@dataclass
class NormalizedQuantity:

    value_type: str

    value: float | None
    value_min: float | None
    value_max: float | None

    unit: str

    converted: bool

    error: str | None = None


def normalize_unit_text(
    unit: str,
) -> str:
    """
    将论文 / LLM 中常见的单位排版转换成
    Pint 更容易理解的形式。

    这里只负责“语法清洗”，
    不负责物理换算。
    """

    text = unit.strip()

    # micro symbol
    text = text.replace(
        "μ",
        "u",
    )

    text = text.replace(
        "µ",
        "u",
    )

    # Unicode minus
    text = text.replace(
        "−",
        "-",
    )

    text = text.replace(
        "–",
        "-",
    )

    # superscript
    text = text.replace(
        "²",
        "^2",
    )

    text = text.replace(
        "³",
        "^3",
    )

    # 常见 PDF 表达：
    #
    # mW cm-2
    # mW.cm-2
    # mW cm^-2
    #
    text = re.sub(
        r"\s*\.\s*",
        " ",
        text,
    )

    text = re.sub(
        r"cm\s*\^?-2",
        "/ cm^2",
        text,
    )

    text = re.sub(
        r"m\s*\^?-2",
        "/ m^2",
        text,
    )

    text = re.sub(
        r"cm\s*\^?-3",
        "/ cm^3",
        text,
    )

    text = re.sub(
        r"m\s*\^?-3",
        "/ m^3",
        text,
    )

    # 合并多余空格
    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


def convert_number(
    value: float | None,
    from_unit: str,
    to_unit: str,
) -> float | None:

    if value is None:
        return None

    quantity = (
        value
        * ureg(from_unit)
    )

    converted = quantity.to(
        to_unit
    )

    return float(
        converted.magnitude
    )


def normalize_fact(
    fact: ExtractedFact,
    metric_spec: MetricSpec,
) -> NormalizedQuantity:
    """
    根据 MetricSpec 中的 canonical_unit
    动态完成单位换算。
    """

    # 没有标准单位时，
    # 保留原始结果
    if not metric_spec.canonical_unit:

        return NormalizedQuantity(
            value_type=fact.value_type,

            value=fact.value,

            value_min=fact.value_min,

            value_max=fact.value_max,

            unit=fact.unit,

            converted=False,

            error=(
                "MetricSpec 未定义 "
                "canonical_unit"
            ),
        )

    from_unit = normalize_unit_text(
        fact.unit
    )

    to_unit = normalize_unit_text(
        metric_spec.canonical_unit
    )

    try:

        return NormalizedQuantity(

            value_type=fact.value_type,

            value=convert_number(
                fact.value,
                from_unit,
                to_unit,
            ),

            value_min=convert_number(
                fact.value_min,
                from_unit,
                to_unit,
            ),

            value_max=convert_number(
                fact.value_max,
                from_unit,
                to_unit,
            ),

            unit=metric_spec.canonical_unit,

            converted=True,

            error=None,
        )

    except (
        UndefinedUnitError,
        DimensionalityError,
        ValueError,
    ) as error:

        # 极其重要：
        #
        # 遇到未知单位绝对不能把原始数据丢掉。
        return NormalizedQuantity(

            value_type=fact.value_type,

            value=fact.value,

            value_min=fact.value_min,

            value_max=fact.value_max,

            unit=fact.unit,

            converted=False,

            error=str(error),
        )