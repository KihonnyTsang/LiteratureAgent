from app.agent.planner import (
    create_plan,
)

from app.agent.executor import (
    execute_plan,
)

from app.agent.answer_context import (
    build_answer_context,
)


def test_answer_context():

    question = (
        "比较所有论文的功率密度，"
        "按从高到低排序，并绘制图表"
    )

    print(
        "用户：",
        question,
    )

    # ========================================================
    # Planner
    # ========================================================

    plan = create_plan(
        question
    )

    print()
    print("=" * 80)
    print("Planner")
    print("=" * 80)

    print(
        plan.model_dump_json(
            indent=2
        )
    )

    # ========================================================
    # Executor
    # ========================================================

    execution = execute_plan(
        plan
    )

    # ========================================================
    # Answer Context
    # ========================================================

    context = (
        build_answer_context(
            execution=execution,
            user_question=question,
        )
    )

    print()
    print("=" * 80)
    print("Answer Context")
    print("=" * 80)

    print(
        context.model_dump_json(
            indent=2
        )
    )

    # ========================================================
    # 单独检查语义
    # ========================================================

    print()
    print("=" * 80)
    print("Semantic Columns")
    print("=" * 80)

    for column in context.columns:

        print(
            f"{column.field}"
            f" -> "
            f"{column.label}"
            f" | role="
            f"{column.role}"
            f" | unit="
            f"{column.unit}"
            f" | visible="
            f"{column.visible}"
        )

    print()
    print("=" * 80)
    print("Operations")
    print("=" * 80)

    for operation in (
        context.operations
    ):

        print(
            operation.model_dump()
        )

    print()
    print("=" * 80)
    print("Plot")
    print("=" * 80)

    print(
        context.plot_path
    )


if __name__ == "__main__":
    test_answer_context()