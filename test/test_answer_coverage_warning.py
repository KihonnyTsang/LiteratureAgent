from app.agent.answer_renderer import (
    build_coverage_warning,
    build_warnings,
    render_final_answer,
    render_final_answer_markdown,
)

from app.agent.answer_schemas import (
    AnswerContext,
)


def make_context(
    metadata: dict,
) -> AnswerContext:

    return AnswerContext(
        user_question="测试覆盖提示",
        user_goal="测试覆盖提示",
        answer_mode="text_and_table",
        metadata=metadata,
    )


def test_incomplete_provenance_coverage_adds_warning():

    context = make_context(
        {
            "coverage_complete":
                False,

            "provenance_coverage_ratio":
                0.04234527687296417,
        }
    )

    warning = build_coverage_warning(
        context
    )

    assert warning is not None
    assert "来源归属覆盖" in warning
    assert "4.2%" in warning
    assert "仍存在未解析候选" in warning
    assert "不应视为完整全库结论" in warning


def test_incomplete_generic_coverage_adds_warning():

    context = make_context(
        {
            "coverage_complete":
                False,

            "coverage_ratio":
                0.5,
        }
    )

    warning = build_coverage_warning(
        context
    )

    assert warning is not None
    assert "覆盖率约为 50.0%" in warning
    assert "不应视为完整全库结论" in warning


def test_complete_coverage_adds_no_coverage_warning():

    context = make_context(
        {
            "coverage_complete":
                True,

            "provenance_coverage_ratio":
                1.0,
        }
    )

    assert (
        build_coverage_warning(
            context
        )
        is None
    )

    assert (
        build_warnings(
            context
        )
        == []
    )


def test_missing_coverage_contract_adds_no_warning():

    context = make_context(
        {}
    )

    assert (
        build_coverage_warning(
            context
        )
        is None
    )


def test_renderer_preserves_deterministic_coverage_warning():

    context = make_context(
        {
            "coverage_complete":
                False,

            "provenance_coverage_ratio":
                0.04234527687296417,
        }
    )

    final_answer = (
        render_final_answer(
            context=context,
            summary=(
                "已完成结构化数据分析。"
            ),
        )
    )

    assert len(
        final_answer.warnings
    ) == 1

    warning = (
        final_answer.warnings[0]
    )

    assert "4.2%" in warning

    markdown = (
        render_final_answer_markdown(
            final_answer
        )
    )

    assert (
        "## 数据质量提示"
        in markdown
    )

    assert warning in markdown
