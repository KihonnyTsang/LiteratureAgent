from app.agent.plan_schemas import (
    AgentPlan,
    ToolStep,
)

from app.agent.plan_validator import (
    PlanValidationError,
    validate_plan,
)


def expect_valid(
    name: str,
    plan: AgentPlan,
):

    print()
    print(
        "=" * 80
    )

    print(
        f"VALID CASE: {name}"
    )

    print(
        "=" * 80
    )

    result = validate_plan(
        plan
    )

    print(
        "通过：",
        result.user_goal,
    )


def expect_invalid(
    name: str,
    plan: AgentPlan,
):

    print()
    print(
        "=" * 80
    )

    print(
        f"INVALID CASE: {name}"
    )

    print(
        "=" * 80
    )

    try:

        validate_plan(
            plan
        )

    except PlanValidationError as error:

        print(
            str(error)
        )

        return

    raise AssertionError(
        f"{name} 本应验证失败，"
        "但 Validator 允许了该计划。"
    )


def test_plan_validator():

    # ========================================================
    # 1. 合法 RAG
    # ========================================================

    valid_rag_plan = AgentPlan(
        user_goal="解释机制",

        steps=[
            ToolStep(
                step_id="step_1",

                tool="rag_search",

                arguments={
                    "question":
                        "为什么加入 "
                        "BaTiO3 后"
                        "压电输出会增强？",

                    "top_k": 5,
                },

                description=(
                    "检索机制解释"
                ),
            )
        ],

        answer_mode="text",
    )

    expect_valid(
        "single rag_search",
        valid_rag_plan,
    )

    # ========================================================
    # 2. 合法 Metadata Pipeline
    # ========================================================

    valid_table_plan = AgentPlan(
        user_goal="按页数排序",

        steps=[
            ToolStep(
                step_id="step_1",

                tool="query_metadata",

                arguments={
                    "fields": [
                        "title",
                        "page_count",
                    ],

                    "scope":
                        "all_documents",
                },
            ),

            ToolStep(
                step_id="step_2",

                tool="sort_table",

                arguments={
                    "input_step":
                        "step_1",

                    "field":
                        "page_count",

                    "order":
                        "descending",
                },
            ),
        ],

        answer_mode=(
            "text_and_table"
        ),
    )

    expect_valid(
        "metadata -> sort",
        valid_table_plan,
    )

    # ========================================================
    # 3. 非法：
    # sort_table 没有 input_step
    # ========================================================

    missing_input_plan = AgentPlan(
        user_goal="错误计划",

        steps=[
            ToolStep(
                step_id="step_1",

                tool="sort_table",

                arguments={
                    "field":
                        "page_count",

                    "order":
                        "descending",
                },
            )
        ],

        answer_mode="table",
    )

    expect_invalid(
        "missing input_step",
        missing_input_plan,
    )

    # ========================================================
    # 4. 非法：
    # input_step 指向未来步骤
    # ========================================================

    future_dependency_plan = (
        AgentPlan(
            user_goal="错误依赖",

            steps=[
                ToolStep(
                    step_id="step_1",

                    tool="sort_table",

                    arguments={
                        "input_step":
                            "step_2",

                        "field":
                            "page_count",

                        "order":
                            "descending",
                    },
                ),

                ToolStep(
                    step_id="step_2",

                    tool="query_metadata",

                    arguments={
                        "fields": [
                            "title",
                            "page_count",
                        ],

                        "scope":
                            "all_documents",
                    },
                ),
            ],

            answer_mode="table",
        )
    )

    expect_invalid(
        "future dependency",
        future_dependency_plan,
    )

    # ========================================================
    # 5. 非法：
    # Tool 不支持这个 argument
    # ========================================================

    unknown_argument_plan = (
        AgentPlan(
            user_goal="错误参数",

            steps=[
                ToolStep(
                    step_id="step_1",

                    tool="rag_search",

                    arguments={
                        "question":
                            "测试",

                        "top_k": 5,

                        "fake_argument":
                            "不应该存在",
                    },
                )
            ],

            answer_mode="text",
        )
    )

    expect_invalid(
        "unknown argument",
        unknown_argument_plan,
    )

    # ========================================================
    # 6. 非法：
    # 参数类型错误
    # ========================================================

    wrong_type_plan = AgentPlan(
        user_goal="错误类型",

        steps=[
            ToolStep(
                step_id="step_1",

                tool="rag_search",

                arguments={
                    "question":
                        "测试",

                    "top_k":
                        "five",
                },
            )
        ],

        answer_mode="text",
    )

    expect_invalid(
        "wrong argument type",
        wrong_type_plan,
    )

    # ========================================================
    # 7. 非法：
    # RAG TextResult 不能交给 sort_table
    # ========================================================

    incompatible_result_plan = (
        AgentPlan(
            user_goal="错误结果类型",

            steps=[
                ToolStep(
                    step_id="step_1",

                    tool="rag_search",

                    arguments={
                        "question":
                            "测试",

                        "top_k": 5,
                    },
                ),

                ToolStep(
                    step_id="step_2",

                    tool="sort_table",

                    arguments={
                        "input_step":
                            "step_1",

                        "field":
                            "value",

                        "order":
                            "descending",
                    },
                ),
            ],

            answer_mode="table",
        )
    )

    expect_invalid(
        "TextResult -> ToolResult pipeline",
        incompatible_result_plan,
    )

    print()
    print(
        "=" * 80
    )

    print(
        "Plan Validator Tests Passed"
    )

    print(
        "=" * 80
    )


if __name__ == "__main__":
    test_plan_validator()


def test_limit_table_plan_validation():

    valid_plan = AgentPlan(
        user_goal="取页数最多的前十篇论文",

        steps=[
            ToolStep(
                step_id="step_1",
                tool="query_metadata",
                arguments={
                    "fields": [
                        "title",
                        "page_count",
                    ],
                    "scope":
                        "all_documents",
                },
            ),

            ToolStep(
                step_id="step_2",
                tool="sort_table",
                arguments={
                    "input_step":
                        "step_1",
                    "field":
                        "page_count",
                    "order":
                        "descending",
                },
            ),

            ToolStep(
                step_id="step_3",
                tool="limit_table",
                arguments={
                    "input_step":
                        "step_2",
                    "limit":
                        10,
                },
            ),
        ],

        answer_mode="text_and_table",
    )

    expect_valid(
        "metadata -> sort -> limit",
        valid_plan,
    )

    missing_input_plan = AgentPlan(
        user_goal="错误 limit 计划",

        steps=[
            ToolStep(
                step_id="step_1",
                tool="limit_table",
                arguments={
                    "limit": 10,
                },
            ),
        ],

        answer_mode="table",
    )

    expect_invalid(
        "limit missing input_step",
        missing_input_plan,
    )

    wrong_type_plan = AgentPlan(
        user_goal="错误 limit 类型",

        steps=[
            ToolStep(
                step_id="step_1",
                tool="query_metadata",
                arguments={
                    "fields": [
                        "title",
                        "page_count",
                    ],
                    "scope":
                        "all_documents",
                },
            ),

            ToolStep(
                step_id="step_2",
                tool="limit_table",
                arguments={
                    "input_step":
                        "step_1",
                    "limit":
                        "10",
                },
            ),
        ],

        answer_mode="table",
    )

    expect_invalid(
        "limit wrong type",
        wrong_type_plan,
    )
