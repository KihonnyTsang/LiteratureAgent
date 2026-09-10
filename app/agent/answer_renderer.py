from typing import Any

from app.agent.answer_schemas import (
    AnswerColumn,
    AnswerContext,
)

from app.agent.final_answer_schemas import (
    FinalAnswer,
)


# ============================================================
# 基础值格式化
# ============================================================

def format_value(
    value: Any,
    column: AnswerColumn,
) -> str:
    """
    确定性格式化。

    不调用 LLM。

    目标：

    0.41020000000000006
    ->
    0.4102

    0.10099999999999999
    ->
    0.101
    """

    if value is None:
        return ""

    # bool 必须放在 int 前面，
    # 因为 Python 中 bool 是 int 子类。
    if isinstance(
        value,
        bool,
    ):

        return (
            "True"
            if value
            else "False"
        )

    if (
        column.format_hint
        == "integer"
    ):

        if isinstance(
            value,
            (int, float),
        ):

            return str(
                int(value)
            )

    if (
        column.format_hint
        == "number"
    ):

        if isinstance(
            value,
            int,
        ):

            return str(
                value
            )

        if isinstance(
            value,
            float,
        ):

            return f"{value:.8g}"

    return str(
        value
    )


# ============================================================
# 列查询
# ============================================================

def get_column_map(
    context: AnswerContext,
) -> dict[str, AnswerColumn]:

    return {
        column.field: column
        for column
        in context.columns
    }


def get_visible_columns(
    context: AnswerContext,
) -> list[AnswerColumn]:

    return [
        column
        for column
        in context.columns
        if column.visible
    ]

# ============================================================
# 科学数值格式化
# ============================================================

def get_measure_companion_fields(
    field: str,
) -> tuple[
    str,
    str,
] | None:
    """
    根据统一 Fact Result 协议，
    获取某个 measure 对应的上下界字段。

    支持：

    value
        -> value_min / value_max

    raw_value
        -> raw_value_min / raw_value_max

    这不是 metric-specific 逻辑。

    它只依赖统一 Scientific Fact
    Result Protocol。
    """

    if field == "value":

        return (
            "value_min",
            "value_max",
        )

    if field == "raw_value":

        return (
            "raw_value_min",
            "raw_value_max",
        )

    return None


def attach_unit(
    rendered: str,
    unit: str | None,
) -> str:
    """
    给已经确定性格式化完成的科学数值附加单位。
    """

    if not rendered:
        return ""

    if not unit:
        return rendered

    return (
        f"{rendered} "
        f"{unit}"
    )


def format_scientific_measure(
    row: dict[str, Any],
    column: AnswerColumn,
) -> str | None:
    """
    尝试按照统一 Scientific Fact Protocol
    格式化科学数值。

    返回：

    str
        已成功按 scientific value 格式化。

    None
        当前列不是 Scientific Fact measure，
        调用方应回退到普通列格式化。

    支持：

    scalar
        10.1 pC/N

    range
        120–960 pC/N

    lower_bound
        > 120 pC/N

    upper_bound
        < 960 pC/N
    """

    # --------------------------------------------------------
    # 只有 measure / raw_measure 才尝试科学数值协议。
    # --------------------------------------------------------

    if column.role not in {
        "measure",
        "raw_measure",
    }:

        return None

    # --------------------------------------------------------
    # 如果没有 value_type，
    # 说明这可能是 aggregate_table 等工具产生的
    # 普通数值列。
    #
    # 此时不应用 Fact range 协议。
    # --------------------------------------------------------

    value_type = row.get(
        "value_type"
    )

    if value_type not in {
        "scalar",
        "range",
        "lower_bound",
        "upper_bound",
    }:

        return None

    # --------------------------------------------------------
    # 当前字段必须属于统一 Fact measure。
    # --------------------------------------------------------

    companion_fields = (
        get_measure_companion_fields(
            column.field
        )
    )

    if companion_fields is None:

        return None

    (
        min_field,
        max_field,
    ) = companion_fields

    # --------------------------------------------------------
    # Unit
    # --------------------------------------------------------

    unit = None

    if column.unit_field:

        unit = row.get(
            column.unit_field
        )

    if (
        not unit
        and column.unit
    ):

        unit = column.unit

    # --------------------------------------------------------
    # Scalar
    # --------------------------------------------------------

    if value_type == "scalar":

        value = row.get(
            column.field
        )

        rendered = format_value(
            value,
            column,
        )

        return attach_unit(
            rendered,
            unit,
        )

    # --------------------------------------------------------
    # Range
    # --------------------------------------------------------

    if value_type == "range":

        value_min = row.get(
            min_field
        )

        value_max = row.get(
            max_field
        )

        if (
            value_min is None
            or value_max is None
        ):

            return ""

        rendered_min = format_value(
            value_min,
            column,
        )

        rendered_max = format_value(
            value_max,
            column,
        )

        rendered = (
            f"{rendered_min}"
            f"–"
            f"{rendered_max}"
        )

        return attach_unit(
            rendered,
            unit,
        )

    # --------------------------------------------------------
    # Lower Bound
    #
    # ExtractedFact 当前协议中：
    # lower_bound 的数值存放在 value。
    # --------------------------------------------------------

    if value_type == "lower_bound":

        value = row.get(
            column.field
        )

        if value is None:
            return ""

        rendered = format_value(
            value,
            column,
        )

        return attach_unit(
            f"> {rendered}",
            unit,
        )

    # --------------------------------------------------------
    # Upper Bound
    # --------------------------------------------------------

    if value_type == "upper_bound":

        value = row.get(
            column.field
        )

        if value is None:
            return ""

        rendered = format_value(
            value,
            column,
        )

        return attach_unit(
            f"< {rendered}",
            unit,
        )

    return None

# ============================================================
# 带单位的显示
# ============================================================

def format_column_value(
    row: dict[str, Any],
    column: AnswerColumn,
) -> str:
    """
    根据 ColumnSpec 语义确定性格式化单元格。

    优先级：

    1. Scientific Fact value protocol
       scalar / range / lower_bound / upper_bound

    2. 普通 column formatting

    例如：

    value_type="range"
    value_min=120
    value_max=960
    unit="pC/N"

    ->

    120–960 pC/N


    page_count=29
    column.unit="页"

    ->

    29 页
    """

    # ========================================================
    # 1. Scientific Fact measure
    # ========================================================

    scientific_value = (
        format_scientific_measure(
            row=row,
            column=column,
        )
    )

    if scientific_value is not None:

        return scientific_value

    # ========================================================
    # 2. 普通字段
    # ========================================================

    raw_value = row.get(
        column.field
    )

    rendered = format_value(
        raw_value,
        column,
    )

    if not rendered:
        return rendered

    # --------------------------------------------------------
    # 单位来自另一列
    # --------------------------------------------------------

    if column.unit_field:

        dynamic_unit = row.get(
            column.unit_field
        )

        if dynamic_unit:

            return (
                f"{rendered} "
                f"{dynamic_unit}"
            )

    # --------------------------------------------------------
    # 固定单位
    # --------------------------------------------------------

    if column.unit:

        return (
            f"{rendered} "
            f"{column.unit}"
        )

    return rendered


# ============================================================
# Table
# ============================================================

def build_table(
    context: AnswerContext,
) -> tuple[
    list[str],
    list[dict[str, str]],
]:
    """
    完全根据 ColumnSpec 构建表格。

    不知道：
    - power density
    - page_count
    - d33
    - voltage

    只认：
    visible
    role
    unit_field
    """

    # 用户没有要求表格
    if "table" not in context.answer_mode:

        return (
            [],
            [],
        )

    visible_columns = (
        get_visible_columns(
            context
        )
    )

    # ========================================================
    # 如果某个 unit 列已经被 measure 通过 unit_field 引用，
    # 就不再单独显示一次。
    #
    # 例如：
    #
    # 输出功率密度 = 135 W/m²
    #
    # 而不是：
    #
    # 输出功率密度 = 135
    # 标准单位 = W/m²
    # ========================================================

    referenced_unit_fields = {
        column.unit_field
        for column
        in visible_columns
        if column.unit_field
    }

    display_columns = [
        column
        for column
        in visible_columns
        if not (
            column.role == "unit"
            and column.field
            in referenced_unit_fields
        )
    ]

    table_columns = [
        column.label
        for column
        in display_columns
    ]

    table_rows = []

    for row in context.rows:

        display_row = {}

        for column in display_columns:

            display_row[
                column.label
            ] = format_column_value(
                row=row,
                column=column,
            )

        table_rows.append(
            display_row
        )

    return (
        table_columns,
        table_rows,
    )


# ============================================================
# Evidence
# ============================================================

def build_evidence_rows(
    context: AnswerContext,
) -> list[dict[str, str]]:
    """
    根据 column role 自动构建 evidence。

    只有存在 role=evidence 的数据集
    才生成 evidence section。
    """

    evidence_columns = [
        column
        for column
        in context.columns
        if column.role == "evidence"
    ]

    if not evidence_columns:

        return []

    dimension_columns = [
        column
        for column
        in context.columns
        if (
            column.role
            == "dimension"
            and column.visible
        )
    ]

    supporting_columns = [
        column
        for column
        in context.columns
        if (
            # Evidence 本身即使 visible=False
            # 也必须进入证据区。
                column.role
                == "evidence"

                # 质量信息也始终保留。
                or column.role
                in {
                    "quality_flag",
                    "quality_issue",
                }

                # 其他辅助字段必须明确 visible=True。
                or (
                        column.visible
                        and column.role
                        in {
                            "reference",
                            "condition",
                            "provenance",
                            "confidence",
                        }
                )
        )
    ]

    result = []

    for row in context.rows:

        has_evidence = any(
            row.get(
                column.field
            )
            not in {
                None,
                "",
            }
            for column
            in evidence_columns
        )

        if not has_evidence:
            continue

        evidence_row = {}

        for column in [
            *dimension_columns,
            *supporting_columns,
        ]:

            value = row.get(
                column.field
            )

            if value is None:
                continue

            evidence_row[
                column.label
            ] = format_value(
                value,
                column,
            )

        result.append(
            evidence_row
        )

    return result


# ============================================================
# Quality warnings
# ============================================================

def format_coverage_ratio(
    value: Any,
) -> str | None:
    """
    将 0~1 的 coverage ratio
    确定性格式化为百分比文本。

    不调用 LLM。
    """

    if (
        isinstance(value, bool)
        or not isinstance(
            value,
            (int, float),
        )
    ):
        return None

    if (
        value < 0
        or value > 1
    ):
        return None

    return f"{value * 100:.1f}%"


def build_coverage_warning(
    context: AnswerContext,
) -> str | None:
    """
    根据统一 metadata coverage contract
    生成确定性数据覆盖提示。

    这里只认通用 metadata：

    coverage_complete
    provenance_coverage_ratio
    coverage_ratio

    不知道具体 metric，
    也不关心是不是 output_power。
    """

    if (
        context.metadata.get(
            "coverage_complete"
        )
        is not False
    ):
        return None

    provenance_ratio = (
        format_coverage_ratio(
            context.metadata.get(
                "provenance_coverage_ratio"
            )
        )
    )

    if provenance_ratio is not None:

        return (
            "当前结构化结果的来源归属覆盖"
            "尚未完整"
            f"（已解析候选约占 {provenance_ratio}）；"
            "仍存在未解析候选，"
            "因此结果仅代表当前已确认数据，"
            "不应视为完整全库结论。"
        )

    coverage_ratio = (
        format_coverage_ratio(
            context.metadata.get(
                "coverage_ratio"
            )
        )
    )

    if coverage_ratio is not None:

        return (
            "当前查询的数据覆盖尚未完整"
            f"（覆盖率约为 {coverage_ratio}）；"
            "结果仅代表当前可用数据，"
            "不应视为完整全库结论。"
        )

    return (
        "当前查询的数据覆盖尚未完整；"
        "结果仅代表当前可用或已确认数据，"
        "不应视为完整全库结论。"
    )


def build_warnings(
    context: AnswerContext,
) -> list[str]:
    """
    生成通用、确定性质量提示。

    来源：

    1. metadata coverage contract
    2. ColumnRole quality_flag / quality_issue

    不知道具体 metric 或业务问题。
    """

    warnings = []

    # ========================================================
    # 1. Dataset-level coverage warning
    # ========================================================

    coverage_warning = (
        build_coverage_warning(
            context
        )
    )

    if coverage_warning:

        warnings.append(
            coverage_warning
        )

    # ========================================================
    # 2. Row-level quality warnings
    # ========================================================

    dimension_column = next(
        (
            column
            for column
            in context.columns
            if (
                column.role
                == "dimension"
                and column.visible
            )
        ),
        None,
    )

    quality_columns = [
        column
        for column
        in context.columns
        if column.role in {
            "quality_flag",
            "quality_issue",
        }
    ]

    for row in context.rows:

        subject = None

        if dimension_column:

            subject = row.get(
                dimension_column.field
            )

        subject_prefix = (
            f"{subject}："
            if subject
            else ""
        )

        for column in quality_columns:

            value = row.get(
                column.field
            )

            if (
                column.role
                == "quality_flag"
                and value is False
            ):

                warnings.append(
                    f"{subject_prefix}"
                    f"{column.label}=False。"
                )

            elif (
                column.role
                == "quality_issue"
                and value
            ):

                warnings.append(
                    f"{subject_prefix}"
                    f"{column.label}："
                    f"{value}"
                )

    return warnings

# ============================================================
# FinalAnswer
# ============================================================

def render_final_answer(
    context: AnswerContext,
    summary: str,
) -> FinalAnswer:
    """
    把 LLM summary + 确定性 AnswerContext
    合并成最终答案。
    """

    (
        table_columns,
        table_rows,
    ) = build_table(
        context
    )

    evidence_rows = (
        build_evidence_rows(
            context
        )
    )

    warnings = build_warnings(
        context
    )

    plot_path = None

    if "plot" in context.answer_mode:

        # 原样使用 Executor 产生的路径。
        # 不允许 LLM 修改。
        plot_path = (
            context.plot_path
        )

    return FinalAnswer(
        summary=summary,

        table_columns=(
            table_columns
        ),

        table_rows=(
            table_rows
        ),

        evidence_rows=(
            evidence_rows
        ),

        plot_path=(
            plot_path
        ),

        warnings=(
            warnings
        ),
    )


# ============================================================
# Markdown
# ============================================================

def escape_markdown(
    value: Any,
) -> str:

    return str(
        value
    ).replace(
        "|",
        "\\|",
    )


def render_markdown_table(
    columns: list[str],
    rows: list[dict[str, Any]],
) -> str:

    if (
        not columns
        or not rows
    ):

        return ""

    lines = [
        "| "
        + " | ".join(
            columns
        )
        + " |",

        "| "
        + " | ".join(
            "---"
            for _
            in columns
        )
        + " |",
    ]

    for row in rows:

        cells = [
            escape_markdown(
                row.get(
                    column,
                    "",
                )
            )
            for column
            in columns
        ]

        lines.append(
            "| "
            + " | ".join(
                cells
            )
            + " |"
        )

    return "\n".join(
        lines
    )


def render_final_answer_markdown(
    answer: FinalAnswer,
) -> str:
    """
    CLI 当前使用的最终 Markdown Renderer。

    未来 Streamlit / FastAPI
    可以直接使用 FinalAnswer 对象，
    不需要依赖这个函数。
    """

    sections = [
        answer.summary
    ]

    # ========================================================
    # Table
    # ========================================================

    table = render_markdown_table(
        answer.table_columns,
        answer.table_rows,
    )

    if table:

        sections.append(
            "## 结果\n\n"
            + table
        )

    # ========================================================
    # Evidence
    # ========================================================

    if answer.evidence_rows:

        evidence_sections = []

        for index, row in enumerate(
            answer.evidence_rows,
            start=1,
        ):

            evidence_sections.append(
                f"### Evidence {index}"
            )

            for (
                label,
                value,
            ) in row.items():

                evidence_sections.append(
                    f"- **{label}**："
                    f"{value}"
                )

        sections.append(
            "## 证据\n\n"
            + "\n".join(
                evidence_sections
            )
        )

    # ========================================================
    # Plot
    # ========================================================

    if answer.plot_path:

        sections.append(
            "## 图表\n\n"
            + answer.plot_path
        )

    # ========================================================
    # Warnings
    # ========================================================

    if answer.warnings:

        sections.append(
            "## 数据质量提示\n\n"
            + "\n".join(
                f"- {warning}"
                for warning
                in answer.warnings
            )
        )

    return "\n\n".join(
        sections
    )