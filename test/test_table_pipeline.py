from app.agent.planner import (
    create_plan,
)

from app.agent.executor import (
    execute_plan,
)


def test_table_pipeline():

    question = (
        "按页数从多到少排列所有论文"
    )

    print(
        "用户：",
        question,
    )

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

    execution = execute_plan(
        plan
    )

    print()
    print("=" * 80)
    print("Final Table")
    print("=" * 80)

    last_step_id = (
        plan.steps[-1].step_id
    )

    result = execution[
        "step_results"
    ][
        last_step_id
    ]

    for row in result.rows:

        print(
            row
        )


if __name__ == "__main__":
    test_table_pipeline()