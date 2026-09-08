from app.agent.planner import (
    create_plan,
)

from app.agent.executor import (
    execute_plan,
)


TEST_QUESTIONS = [

    "所有论文平均多少页？",

    "所有论文总共有多少页？",
]


def test_aggregate_pipeline():

    for question in TEST_QUESTIONS:

        print()
        print("=" * 80)

        print(
            "用户：",
            question,
        )

        # ====================================================
        # Planner
        # ====================================================

        plan = create_plan(
            question
        )

        print()
        print("Planner:")
        print(
            plan.model_dump_json(
                indent=2
            )
        )

        # ====================================================
        # Executor
        # ====================================================

        execution = execute_plan(
            plan
        )

        last_step_id = (
            plan.steps[-1].step_id
        )

        result = execution[
            "step_results"
        ][
            last_step_id
        ]

        print()
        print("Result:")

        for row in result.rows:

            print(
                row
            )


if __name__ == "__main__":
    test_aggregate_pipeline()