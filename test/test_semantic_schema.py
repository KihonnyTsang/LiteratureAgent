from app.agent.planner import (
    create_plan,
)

from app.agent.executor import (
    execute_plan,
)


def test_semantic_schema():

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

    execution = execute_plan(
        plan
    )

    # ========================================================
    # 检查每一步 Schema
    # ========================================================

    for step in plan.steps:

        result = execution[
            "step_results"
        ][
            step.step_id
        ]

        print()
        print("=" * 80)

        print(
            "Step:",
            step.step_id,
            step.tool,
        )

        print(
            "Columns:",
            result.columns,
        )

        print()
        print("Column Specs:")

        for spec in (
            result.column_specs
        ):

            print(
                spec.model_dump()
            )

    # ========================================================
    # 最终检查 value
    # ========================================================

    final_result = execution[
        "step_results"
    ][
        plan.steps[-1].step_id
    ]

    value_spec = (
        final_result
        .get_column_spec(
            "value"
        )
    )

    print()
    print("=" * 80)
    print("Final value semantic")
    print("=" * 80)

    print(
        value_spec.model_dump()
        if value_spec
        else None
    )


if __name__ == "__main__":
    test_semantic_schema()