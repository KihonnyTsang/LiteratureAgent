import inspect

from typing import (
    Any,
    get_type_hints,
)

from pydantic import (
    TypeAdapter,
    ValidationError,
)

from app.agent.plan_schemas import (
    AgentPlan,
    ToolStep,
)

from app.tools.registry import (
    TOOL_REGISTRY,
)


MAX_PLAN_STEPS = 12


class PlanValidationError(
    ValueError
):
    """
    AgentPlan 没有通过确定性验证。
    """

    def __init__(
        self,
        errors: list[str],
    ):

        self.errors = errors

        message = (
            "AgentPlan 验证失败：\n"
            + "\n".join(
                f"- {error}"
                for error
                in errors
            )
        )

        super().__init__(
            message
        )


def get_type_hints_safe(
    function,
) -> dict[str, Any]:
    """
    尝试获取 Tool 的类型注解。

    某些复杂 annotation 无法解析时，
    不让 Validator 本身崩溃。
    """

    try:

        return get_type_hints(
            function
        )

    except Exception:

        return {}


def get_tool_function(
    tool_name: str,
):
    """
    从 Tool Registry 获取真实 Tool。
    """

    return TOOL_REGISTRY.get(
        tool_name
    )


def get_required_parameters(
    function,
) -> list[str]:
    """
    获取 Tool 中没有默认值的必需参数。
    """

    signature = inspect.signature(
        function
    )

    required = []

    for (
        name,
        parameter,
    ) in signature.parameters.items():

        if parameter.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            continue

        if (
            parameter.default
            is inspect.Parameter.empty
        ):

            required.append(
                name
            )

    return required


def function_accepts_parameter(
    function,
    parameter_name: str,
) -> bool:
    """
    Tool 是否接受某参数。

    如果 Tool 有 **kwargs，
    也认为能够接受。
    """

    signature = inspect.signature(
        function
    )

    if (
        parameter_name
        in signature.parameters
    ):
        return True

    return any(
        parameter.kind
        == inspect.Parameter.VAR_KEYWORD

        for parameter
        in signature.parameters.values()
    )


def validate_argument_type(
    function,
    argument_name: str,
    value: Any,
) -> str | None:
    """
    使用 Tool 自己的 Python type annotation
    验证 Planner 给出的参数。

    不维护第二套业务参数 Schema。
    """

    signature = inspect.signature(
        function
    )

    parameter = (
        signature.parameters.get(
            argument_name
        )
    )

    if parameter is None:
        return None

    type_hints = (
        get_type_hints_safe(
            function
        )
    )

    annotation = (
        type_hints.get(
            argument_name,
            parameter.annotation,
        )
    )

    if (
        annotation
        is inspect.Parameter.empty
    ):
        return None

    try:

        TypeAdapter(
            annotation
        ).validate_python(
            value,
            strict=True,
        )

    except (
        ValidationError,
        TypeError,
        ValueError,
    ) as error:

        return (
            f"参数 {argument_name!r} "
            f"类型不符合 Tool Contract："
            f"{error}"
        )

    return None


def validate_result_compatibility(
    previous_function,
    current_function,
) -> str | None:
    """
    尝试利用 Tool 的 return annotation
    和 input_table annotation
    检查上下游类型兼容性。

    例如：

    rag_search -> TextResult

    不能作为：

    sort_table(input_table: ToolResult)

    的输入。

    如果 Tool 没有足够的 annotation，
    则跳过该项检查。
    """

    previous_hints = (
        get_type_hints_safe(
            previous_function
        )
    )

    current_hints = (
        get_type_hints_safe(
            current_function
        )
    )

    output_type = (
        previous_hints.get(
            "return"
        )
    )

    input_type = (
        current_hints.get(
            "input_table"
        )
    )

    if (
        output_type is None
        or input_type is None
    ):
        return None

    # 当前只对普通 class annotation
    # 做安全的 issubclass 判断。
    if not isinstance(
        output_type,
        type,
    ):
        return None

    if not isinstance(
        input_type,
        type,
    ):
        return None

    try:

        compatible = issubclass(
            output_type,
            input_type,
        )

    except TypeError:

        return None

    if compatible:
        return None

    return (
        "上游 Tool 返回类型 "
        f"{output_type.__name__} "
        "不能作为当前 Tool 的 "
        f"{input_type.__name__} 输入。"
    )


def validate_step(
    step: ToolStep,
    previous_steps: dict[
        str,
        ToolStep,
    ],
) -> list[str]:
    """
    验证单个 Planner Step。
    """

    errors = []

    # ========================================================
    # 1. Tool 是否注册
    # ========================================================

    function = get_tool_function(
        step.tool
    )

    if function is None:

        errors.append(
            f"{step.step_id}: "
            f"Tool {step.tool!r} "
            "没有注册到 TOOL_REGISTRY。"
        )

        return errors

    arguments = dict(
        step.arguments
    )

    # ========================================================
    # 2. 禁止 Planner 直接传 input_table
    #
    # input_table 是 Runtime Object，
    # 必须由 Executor 注入。
    # ========================================================

    if "input_table" in arguments:

        errors.append(
            f"{step.step_id}: "
            "Planner 不允许直接提供 "
            "'input_table'。"
            "应使用 'input_step'。"
        )

    # ========================================================
    # 3. input_step dependency
    # ========================================================

    input_step = arguments.get(
        "input_step"
    )

    has_input_step = (
        "input_step"
        in arguments
    )

    if has_input_step:

        if not isinstance(
            input_step,
            str,
        ):

            errors.append(
                f"{step.step_id}: "
                "'input_step' 必须是字符串。"
            )

        elif (
            input_step
            not in previous_steps
        ):

            errors.append(
                f"{step.step_id}: "
                f"input_step={input_step!r} "
                "没有引用之前已经完成的步骤。"
            )

        # 当前 Tool 必须真的接受 input_table
        if not function_accepts_parameter(
            function,
            "input_table",
        ):

            errors.append(
                f"{step.step_id}: "
                f"Tool {step.tool!r} "
                "不接受上游表格输入，"
                "但 Planner 提供了 input_step。"
            )

    # ========================================================
    # 4. 如果 Tool 强制需要 input_table，
    # Planner 必须提供 input_step
    # ========================================================

    required_parameters = (
        get_required_parameters(
            function
        )
    )

    if (
        "input_table"
        in required_parameters
        and not has_input_step
    ):

        errors.append(
            f"{step.step_id}: "
            f"Tool {step.tool!r} "
            "需要上游 input_table，"
            "但 Planner 没有提供 input_step。"
        )

    # ========================================================
    # 5. Planner arguments -> Runtime arguments
    # ========================================================

    runtime_argument_names = {
        name
        for name
        in arguments
        if name
        not in {
            "input_step",
            "input_table",
        }
    }

    signature = inspect.signature(
        function
    )

    has_var_keyword = any(
        parameter.kind
        == inspect.Parameter.VAR_KEYWORD

        for parameter
        in signature.parameters.values()
    )

    # ========================================================
    # 6. Unknown arguments
    # ========================================================

    if not has_var_keyword:

        allowed_arguments = set(
            signature.parameters
        )

        # input_table 由 Executor 注入，
        # 不属于 Planner 直接参数。
        allowed_arguments.discard(
            "input_table"
        )

        unknown_arguments = (
            runtime_argument_names
            - allowed_arguments
        )

        for argument_name in sorted(
            unknown_arguments
        ):

            errors.append(
                f"{step.step_id}: "
                f"Tool {step.tool!r} "
                f"不支持参数 "
                f"{argument_name!r}。"
            )

    # ========================================================
    # 7. Missing required arguments
    # ========================================================

    for required_name in (
        required_parameters
    ):

        if required_name == (
            "input_table"
        ):
            continue

        if (
            required_name
            not in arguments
        ):

            errors.append(
                f"{step.step_id}: "
                f"Tool {step.tool!r} "
                f"缺少必需参数 "
                f"{required_name!r}。"
            )

    # ========================================================
    # 8. Argument type validation
    # ========================================================

    for (
        argument_name,
        value,
    ) in arguments.items():

        if argument_name in {
            "input_step",
            "input_table",
        }:
            continue

        if (
            argument_name
            not in signature.parameters
        ):
            continue

        type_error = (
            validate_argument_type(
                function=function,
                argument_name=(
                    argument_name
                ),
                value=value,
            )
        )

        if type_error:

            errors.append(
                f"{step.step_id}: "
                f"{type_error}"
            )

    # ========================================================
    # 9. 上下游 Result 类型兼容
    # ========================================================

    if (
        has_input_step
        and isinstance(
            input_step,
            str,
        )
        and input_step
        in previous_steps
    ):

        previous_step = (
            previous_steps[
                input_step
            ]
        )

        previous_function = (
            get_tool_function(
                previous_step.tool
            )
        )

        if (
            previous_function
            is not None
        ):

            compatibility_error = (
                validate_result_compatibility(
                    previous_function=(
                        previous_function
                    ),
                    current_function=(
                        function
                    ),
                )
            )

            if compatibility_error:

                errors.append(
                    f"{step.step_id}: "
                    f"{compatibility_error}"
                )

    return errors


def validate_plan(
    plan: AgentPlan,
) -> AgentPlan:
    """
    确定性验证 Planner 输出。

    成功：
        原样返回 AgentPlan。

    失败：
        抛出 PlanValidationError。

    Validator 不修改 Planner 的计划，
    只判断这个计划是否允许进入 Executor。
    """

    errors = []

    # ========================================================
    # 1. Plan size
    # ========================================================

    if not plan.steps:

        errors.append(
            "AgentPlan 至少需要一个步骤。"
        )

    if (
        len(plan.steps)
        > MAX_PLAN_STEPS
    ):

        errors.append(
            "AgentPlan 步骤过多："
            f"{len(plan.steps)} > "
            f"{MAX_PLAN_STEPS}。"
        )

    # ========================================================
    # 2. Unique step IDs
    # ========================================================

    seen_step_ids = set()

    for step in plan.steps:

        if not step.step_id.strip():

            errors.append(
                "step_id 不能为空。"
            )

        if (
            step.step_id
            in seen_step_ids
        ):

            errors.append(
                "出现重复 step_id："
                f"{step.step_id!r}。"
            )

        seen_step_ids.add(
            step.step_id
        )

    # ========================================================
    # 3. Sequential validation
    # ========================================================

    previous_steps = {}

    for step in plan.steps:

        step_errors = (
            validate_step(
                step=step,
                previous_steps=(
                    previous_steps
                ),
            )
        )

        errors.extend(
            step_errors
        )

        previous_steps[
            step.step_id
        ] = step

    # ========================================================
    # 4. Fail
    # ========================================================

    if errors:

        raise PlanValidationError(
            errors
        )

    return plan