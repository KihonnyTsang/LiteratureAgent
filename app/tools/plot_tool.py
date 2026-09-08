import re
import uuid
from pathlib import Path

import matplotlib

matplotlib.use(
    "Agg"
)

import matplotlib.pyplot as plt
from matplotlib import font_manager

from app.tools.schemas import ToolResult


PROJECT_ROOT = Path(
    __file__
).resolve().parents[2]

PLOTS_DIR = (
    PROJECT_ROOT
    / "data"
    / "plots"
)

PLOTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def configure_font():
    """
    尝试配置中英文兼容字体。
    """

    preferred_fonts = [
        "PingFang SC",
        "Hiragino Sans GB",
        "Heiti SC",
        "Microsoft YaHei",
        "SimHei",
        "Arial Unicode MS",
    ]

    installed_fonts = {}

    for font_path in font_manager.findSystemFonts():

        try:
            font_name = (
                font_manager
                .FontProperties(
                    fname=font_path
                )
                .get_name()
            )

            installed_fonts[
                font_name
            ] = font_path

        except Exception:
            continue

    for font_name in preferred_fonts:

        if font_name in installed_fonts:

            plt.rcParams[
                "font.family"
            ] = [
                font_name,
                "DejaVu Sans",
            ]

            plt.rcParams[
                "axes.unicode_minus"
            ] = False

            plt.rcParams[
                "mathtext.fontset"
            ] = "dejavusans"

            plt.rcParams[
                "mathtext.default"
            ] = "regular"

            return font_name

    return None


configure_font()


def make_plot_filename(
    title: str,
) -> str:
    """
    根据标题生成安全文件名。
    """

    safe_title = re.sub(
        r"[^\w\u4e00-\u9fff]+",
        "_",
        title,
    )

    safe_title = (
        safe_title.strip("_")
    )

    if not safe_title:
        safe_title = "plot"

    unique_id = (
        uuid.uuid4()
        .hex[:8]
    )

    return (
        f"{safe_title}_{unique_id}.png"
    )

def shorten_label(
    value,
    max_length: int = 42,
) -> str:
    """
    缩短过长的类别标签。

    完整数据不会丢失，
    只是图表显示时进行截断。
    """

    text = str(value)

    if len(text) <= max_length:
        return text

    return (
        text[:max_length - 1]
        + "…"
    )


def should_use_horizontal_bar(
    labels: list[str],
) -> bool:
    """
    自动判断柱状图是否应该横向显示。

    类别较多或者标签较长时，
    横向柱状图通常可读性更好。
    """

    if len(labels) >= 6:
        return True

    if not labels:
        return False

    average_length = (
        sum(
            len(label)
            for label in labels
        )
        / len(labels)
    )

    max_length = max(
        len(label)
        for label in labels
    )

    return (
        average_length >= 18
        or max_length >= 28
    )

def infer_numeric_scale(
    values: list[float],
    requested_scale: str = "auto",
) -> str:
    """
    自动判断数值轴使用 linear 还是 log。

    只有全部有效值都 > 0 时才允许 log。
    动态范围 >= 100 时自动使用 log。
    """

    if requested_scale not in {
        "auto",
        "linear",
        "log",
    }:
        raise ValueError(
            f"未知 scale：{requested_scale}"
        )

    if requested_scale != "auto":
        return requested_scale

    numeric_values = [
        float(value)
        for value in values
        if isinstance(value, (int, float))
    ]

    if not numeric_values:
        return "linear"

    if any(
        value <= 0
        for value in numeric_values
    ):
        return "linear"

    minimum = min(numeric_values)
    maximum = max(numeric_values)

    if minimum == 0:
        return "linear"

    dynamic_range = (
        maximum / minimum
    )

    if dynamic_range >= 100:
        return "log"

    return "linear"


def get_semantic_axis_label(
    input_table: ToolResult,
    field: str,
) -> str:
    """
    根据 ColumnSpec 自动生成坐标轴名称。

    Plot Tool 不需要知道：

    - power density
    - d33
    - page_count
    - voltage

    它只读取字段语义。
    """

    spec = input_table.get_column_spec(
        field
    )

    if spec is None:
        return field

    label = spec.label

    if spec.unit:

        return (
            f"{label} "
            f"({spec.unit})"
        )

    return label

def plot_table(
    input_table: ToolResult,
    chart_type: str,
    x: str,
    y: str,
    title: str | None = None,
    orientation: str = "auto",
    scale: str = "auto",
) -> ToolResult:
    """
    对任意 ToolResult 进行通用绘图。

    支持：
    - bar
    - line
    - scatter
    - pie

    bar 图会根据类别数量和标签长度
    自动选择横向或纵向布局。
    """

    # ========================================================
    # 1. 字段检查
    # ========================================================

    if x not in input_table.columns:
        raise ValueError(
            f"绘图字段不存在：{x}"
        )

    if y not in input_table.columns:
        raise ValueError(
            f"绘图字段不存在：{y}"
        )

    if chart_type not in {
        "bar",
        "line",
        "scatter",
        "pie",
    }:
        raise ValueError(
            f"不支持的图表类型：{chart_type}"
        )

    if orientation not in {
        "auto",
        "horizontal",
        "vertical",
    }:
        raise ValueError(
            f"未知 orientation："
            f"{orientation}"
        )

    # ========================================================
    # 2. 去除无法绘图的空数据
    # ========================================================

    rows = [
        row
        for row in input_table.rows
        if (
            row.get(x) is not None
            and row.get(y) is not None
        )
    ]

    if not rows:
        raise ValueError(
            "没有可用于绘图的数据。"
        )

    raw_x_values = [
        row[x]
        for row in rows
    ]

    y_values = [
        row[y]
        for row in rows
    ]

    # ========================================================
    # 自动判断数值轴使用 linear / log
    # ========================================================

    resolved_scale = infer_numeric_scale(
        y_values,
        requested_scale=scale,
    )

    # ========================================================
    # 自动生成有语义的坐标轴名称
    #
    # 例如：
    # value
    # ->
    # 功率密度 (W/m²)
    # ========================================================

    y_axis_label = get_semantic_axis_label(
        input_table,
        y,
    )

    labels = [
        shorten_label(value)
        for value in raw_x_values
    ]

    if title is None:
        title = f"{y} by {x}"

    # ========================================================
    # 3. Bar
    # ========================================================

    if chart_type == "bar":

        use_horizontal = False

        if orientation == "horizontal":

            use_horizontal = True

        elif orientation == "vertical":

            use_horizontal = False

        else:

            use_horizontal = (
                should_use_horizontal_bar(
                    labels
                )
            )

        # ----------------------------------------------------
        # 横向柱状图
        # ----------------------------------------------------

        if use_horizontal:

            figure_height = max(
                5.0,
                len(rows) * 0.65 + 1.5,
            )

            fig, ax = plt.subplots(
                figsize=(
                    12,
                    figure_height,
                )
            )

            bars = ax.barh(
                labels,
                y_values,
            )

            if resolved_scale == "log":
                ax.set_xscale("log")

            # 第一条数据显示在最上方
            ax.invert_yaxis()

            ax.set_xlabel(
                y_axis_label
            )

            ax.set_ylabel(
                x
            )

            # 每个柱子显示数值
            for bar, value in zip(
                    bars,
                    y_values,
            ):
                ax.annotate(
                    f"{value:.6g}",
                    xy=(
                        bar.get_width(),
                        bar.get_y()
                        + bar.get_height() / 2,
                    ),
                    xytext=(6, 0),
                    textcoords="offset points",
                    va="center",
                    ha="left",
                )

        # ----------------------------------------------------
        # 纵向柱状图
        # ----------------------------------------------------

        else:

            fig, ax = plt.subplots(
                figsize=(12, 7)
            )

            bars = ax.bar(
                labels,
                y_values,
            )

            if resolved_scale == "log":
                ax.set_yscale("log")

            ax.set_xlabel(
                x
            )

            ax.set_ylabel(
                y_axis_label
            )

            ax.tick_params(
                axis="x",
                rotation=30,
            )

            for label in (
                ax.get_xticklabels()
            ):

                label.set_ha(
                    "right"
                )

            for bar, value in zip(
                    bars,
                    y_values,
            ):
                ax.annotate(
                    f"{value:.6g}",
                    xy=(
                        bar.get_x()
                        + bar.get_width() / 2,
                        bar.get_height(),
                    ),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                )

    # ========================================================
    # 4. Line
    # ========================================================

    elif chart_type == "line":

        fig, ax = plt.subplots(
            figsize=(12, 7)
        )

        ax.plot(
            labels,
            y_values,
            marker="o",
        )

        ax.set_xlabel(
            x
        )

        ax.set_ylabel(
            y
        )

        ax.tick_params(
            axis="x",
            rotation=30,
        )

    # ========================================================
    # 5. Scatter
    # ========================================================

    elif chart_type == "scatter":

        fig, ax = plt.subplots(
            figsize=(10, 7)
        )

        ax.scatter(
            raw_x_values,
            y_values,
        )

        ax.set_xlabel(
            x
        )

        ax.set_ylabel(
            y
        )

    # ========================================================
    # 6. Pie
    # ========================================================

    else:

        fig, ax = plt.subplots(
            figsize=(9, 9)
        )

        ax.pie(
            y_values,
            labels=labels,
            autopct="%1.1f%%",
        )

    # ========================================================
    # 7. 通用图表设置
    # ========================================================

    ax.set_title(
        title
    )

    ax.grid(
        axis="y"
        if chart_type == "bar"
        and not use_horizontal
        else "x",
        alpha=0.2,
    )

    fig.tight_layout()

    # ========================================================
    # 8. 保存
    # ========================================================

    filename = make_plot_filename(
        title
    )

    output_path = (
        PLOTS_DIR
        / filename
    )

    fig.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close(
        fig
    )

    # ========================================================
    # 9. ToolResult
    # ========================================================

    return ToolResult(
        columns=input_table.columns,

        rows=input_table.rows,

        column_specs=[
            spec.model_copy(
                deep=True
            )
            for spec
            in input_table.column_specs
        ],

        metadata={
            **input_table.metadata,

            "plot_path":
                str(output_path),

            "chart_type":
                chart_type,

            "plot_x":
                x,

            "plot_y":
                y,

            "plot_title":
                title,

            "value_scale":
                resolved_scale,

            "orientation":
                (
                    (
                        "horizontal"
                        if use_horizontal
                        else "vertical"
                    )
                    if chart_type == "bar"
                    else None
                ),
        },
    )