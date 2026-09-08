from pathlib import Path

import app.tools.plot_tool as plot_tool

from app.tools.schemas import (
    ColumnSpec,
    ToolResult,
)


def test_plot_pipeline(
    tmp_path,
    monkeypatch,
) -> None:
    """
    验证 Plot Tool 的确定性行为。

    使用 pytest tmp_path，
    不把测试图片写进正式：

        data/plots/

    不依赖：

    - Planner
    - LLM
    - SQLite
    - Qdrant
    """

    monkeypatch.setattr(
        plot_tool,
        "PLOTS_DIR",
        tmp_path,
    )

    input_table = ToolResult(
        columns=[
            "title",
            "page_count",
        ],

        rows=[
            {
                "title": "Paper A",
                "page_count": 10,
            },
            {
                "title": "Paper B",
                "page_count": 30,
            },
            {
                "title": "Paper C",
                "page_count": 20,
            },
        ],

        column_specs=[
            ColumnSpec(
                field="title",
                label="论文",
                role="identifier",
                visible=True,
                format_hint="text",
            ),
            ColumnSpec(
                field="page_count",
                label="页数",
                role="measure",
                visible=True,
                format_hint="number",
            ),
        ],

        metadata={
            "source": "synthetic_test",
        },
    )

    result = plot_tool.plot_table(
        input_table=input_table,
        chart_type="bar",
        x="title",
        y="page_count",
        title="Page Count Test",
        orientation="vertical",
        scale="linear",
    )

    # ========================================================
    # Plot file
    # ========================================================

    plot_path = Path(
        result.metadata[
            "plot_path"
        ]
    )

    assert plot_path.exists()

    assert plot_path.is_file()

    assert (
        plot_path.parent
        == tmp_path
    )

    assert (
        plot_path.suffix
        == ".png"
    )

    # ========================================================
    # Metadata
    # ========================================================

    assert (
        result.metadata[
            "chart_type"
        ]
        == "bar"
    )

    assert (
        result.metadata[
            "plot_x"
        ]
        == "title"
    )

    assert (
        result.metadata[
            "plot_y"
        ]
        == "page_count"
    )

    assert (
        result.metadata[
            "plot_title"
        ]
        == "Page Count Test"
    )

    assert (
        result.metadata[
            "value_scale"
        ]
        == "linear"
    )

    assert (
        result.metadata[
            "orientation"
        ]
        == "vertical"
    )

    assert (
        result.metadata[
            "source"
        ]
        == "synthetic_test"
    )

    # ========================================================
    # Table preservation
    # ========================================================

    assert (
        result.rows
        == input_table.rows
    )

    assert (
        result.columns
        == input_table.columns
    )