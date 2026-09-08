from pathlib import Path

import pytest

from app.agent.planner import (
    create_plan,
)

from app.agent.executor import (
    execute_plan,
)

from app.agent.answer_context import (
    build_answer_context,
)

from app.agent.answer_writer import (
    write_summary,
)

from app.agent.answer_renderer import (
    render_final_answer,
    render_final_answer_markdown,
)


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.slow
def test_answer_writer_power_density_integrity() -> None:
    """
    完整验证定量结构化回答：

        Planner
        → Executor
        → AnswerContext
        → Answer Writer
        → Deterministic Renderer

    重点锁定：

    1. Plot path 不被 LLM 修改
    2. 表格数值不被 LLM 改写
    3. 排名结果保持正确
    4. Markdown 可以正常渲染

    会使用真实：

    - LLM
    - SQLite facts
    - Plot pipeline

    因此属于 integration + llm + slow。
    """

    question = (
        "比较所有论文的功率密度，"
        "按从高到低排序，并绘制图表"
    )

    # ========================================================
    # 1. Planner
    # ========================================================

    plan = create_plan(
        question
    )

    # ========================================================
    # 2. Executor
    # ========================================================

    execution = execute_plan(
        plan
    )

    # ========================================================
    # 3. Answer Context
    # ========================================================

    context = build_answer_context(
        execution=execution,
        user_question=question,
    )

    assert context.rows

    # ========================================================
    # 4. LLM Summary
    # ========================================================

    summary = write_summary(
        context
    )

    assert summary.strip()

    # ========================================================
    # 5. Deterministic Renderer
    # ========================================================

    final_answer = render_final_answer(
        context=context,
        summary=summary,
    )

    markdown = (
        render_final_answer_markdown(
            final_answer
        )
    )

    assert markdown.strip()

    # ========================================================
    # 6. Plot integrity
    # ========================================================

    assert (
        final_answer.plot_path
        == context.plot_path
    )

    assert (
        final_answer.plot_path
        is not None
    )

    assert Path(
        final_answer.plot_path
    ).exists()

    # ========================================================
    # 7. Table integrity
    # ========================================================

    assert final_answer.table_rows

    siddiqui_rows = [
        row
        for row
        in final_answer.table_rows
        if "Siddiqui"
        in row.get(
            "论文",
            "",
        )
    ]

    assert siddiqui_rows

    assert (
        siddiqui_rows[0].get(
            "输出功率密度"
        )
        == "135 W/m²"
    )

    rana_rows = [
        row
        for row
        in final_answer.table_rows
        if "Rana"
        in row.get(
            "论文",
            "",
        )
    ]

    assert rana_rows

    assert (
        rana_rows[0].get(
            "输出功率密度"
        )
        == "0.4102 W/m²"
    )