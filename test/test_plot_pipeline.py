from app.agent.planner import (
    create_plan,
)

from app.agent.executor import (
    execute_plan,
)


def test_plot_pipeline():

    question = (
        "统计所有 paper 的页数，并绘制图表"
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
    # 最终结果
    # ========================================================

    last_step_id = (
        plan.steps[-1].step_id
    )

    result = execution[
        "step_results"
    ][
        last_step_id
    ]

    print()
    print("=" * 80)
    print("Final Table")
    print("=" * 80)

    for row in result.rows:

        print(
            row
        )

    print()
    print("=" * 80)
    print("Plot")
    print("=" * 80)

    print(
        result.metadata.get(
            "plot_path"
        )
    )


if __name__ == "__main__":
    test_plot_pipeline()