from app.tools.schemas import ToolResult

from statistics import mean, median


from statistics import mean, median

from app.tools.schemas import (
    ColumnSpec,
    ToolResult,
)

def copy_column_spec(
    input_table: ToolResult,
    field: str,
):
    """
    从输入表复制某字段的 ColumnSpec。
    """

    spec = input_table.get_column_spec(
        field
    )

    if spec is None:
        return None

    return spec.model_copy(
        deep=True
    )


def build_aggregate_value_spec(
    input_table: ToolResult,
    field: str | None,
    operation: str,
) -> ColumnSpec:
    """
    给聚合后的 value 字段生成语义。
    """

    if operation == "count":

        return ColumnSpec(
            field="value",
            label="数量",
            role="measure",
            visible=True,
            format_hint="integer",
        )

    source_spec = None

    if field is not None:

        source_spec = (
            input_table
            .get_column_spec(
                field
            )
        )

    if source_spec is None:

        return ColumnSpec(
            field="value",
            label=field or "值",
            role="measure",
            visible=True,
            format_hint="number",
        )

    return ColumnSpec(
        field="value",

        # measure 的业务语义继续继承
        label=source_spec.label,

        role="measure",

        visible=True,

        format_hint=(
            source_spec.format_hint
            or "number"
        ),

        unit=source_spec.unit,
    )

def aggregate_table(
    input_table: ToolResult,
    operation: str,
    field: str | None = None,
    group_by: str | list[str] | None = None,
) -> ToolResult:
    """
    对任意 ToolResult 做确定性统计。

    支持：

    max
    min
    mean
    median
    sum
    count

    特别规则：

    max / min
    会保留产生极值的完整原始 row。

    这样科研数据在聚合以后仍然保留：

    raw_value
    raw_unit
    page_number
    evidence
    condition_text
    provenance
    confidence
    等来源信息。
    """

    supported_operations = {
        "max",
        "min",
        "mean",
        "median",
        "sum",
        "count",
    }

    if operation not in supported_operations:

        raise ValueError(
            f"不支持的聚合操作："
            f"{operation}"
        )

    # ========================================================
    # 1. group_by 标准化
    # ========================================================

    if group_by is None:

        group_fields = []

    elif isinstance(
        group_by,
        str,
    ):

        group_fields = [
            group_by
        ]

    else:

        group_fields = list(
            group_by
        )

    # ========================================================
    # 2. 字段验证
    # ========================================================

    for group_field in group_fields:

        if (
            group_field
            not in input_table.columns
        ):

            raise ValueError(
                f"group_by 字段不存在："
                f"{group_field}"
            )

    if (
        operation != "count"
        and field is None
    ):

        raise ValueError(
            f"{operation} 操作必须指定 field。"
        )

    if (
        field is not None
        and field
        not in input_table.columns
    ):

        raise ValueError(
            f"聚合字段不存在："
            f"{field}"
        )

    # ========================================================
    # 3. 获取有效数值行
    # ========================================================

    def get_numeric_rows(
        rows: list[dict],
    ) -> list[dict]:

        if field is None:
            return rows

        valid_rows = []

        for row in rows:

            value = row.get(
                field
            )

            if value is None:
                continue

            if not isinstance(
                value,
                (int, float),
            ):

                raise ValueError(
                    f"字段 {field} "
                    f"包含非数值数据："
                    f"{value}"
                )

            valid_rows.append(
                row
            )

        return valid_rows

    # ========================================================
    # 4. 普通数值聚合
    # ========================================================

    def calculate_value(
        rows: list[dict],
    ):

        if operation == "count":

            if field is None:

                return len(
                    rows
                )

            return sum(
                1
                for row in rows
                if row.get(field)
                is not None
            )

        numeric_rows = (
            get_numeric_rows(
                rows
            )
        )

        if not numeric_rows:
            return None

        values = [
            row[field]
            for row in numeric_rows
        ]

        if operation == "mean":

            return mean(
                values
            )

        if operation == "median":

            return median(
                values
            )

        if operation == "sum":

            return sum(
                values
            )

        if operation == "max":

            return max(
                values
            )

        if operation == "min":

            return min(
                values
            )

        raise ValueError(
            f"未知 operation："
            f"{operation}"
        )

    # ========================================================
    # 5. max / min：
    #
    # 返回产生极值的完整原始 row
    # ========================================================

    def select_extreme_row(
        rows: list[dict],
    ) -> dict | None:

        numeric_rows = (
            get_numeric_rows(
                rows
            )
        )

        if not numeric_rows:
            return None

        if operation == "max":

            return max(
                numeric_rows,
                key=lambda row:
                    row[field],
            )

        if operation == "min":

            return min(
                numeric_rows,
                key=lambda row:
                    row[field],
            )

        return None

    # ========================================================
    # 6. 不分组
    # ========================================================

    if not group_fields:

        # ----------------------------------------------------
        # MAX / MIN：
        # 保留完整来源 row
        # ----------------------------------------------------

        if operation in {
            "max",
            "min",
        }:

            selected_row = (
                select_extreme_row(
                    input_table.rows
                )
            )

            if selected_row is None:

                return ToolResult(
                    columns=input_table.columns,
                    rows=[],
                    column_specs=[
                        spec.model_copy(
                            deep=True
                        )
                        for spec
                        in input_table.column_specs
                    ],
                    metadata={
                        **input_table.metadata,
                        "aggregation":
                            operation,
                        "aggregation_field":
                            field,
                        "group_by":
                            None,
                    },
                )

            result_row = dict(
                selected_row
            )

            return ToolResult(
                columns=input_table.columns,

                rows=[
                    result_row
                ],
                column_specs=[
                    spec.model_copy(
                        deep=True
                    )
                    for spec
                    in input_table.column_specs
                ],

                metadata={
                    **input_table.metadata,

                    "aggregation":
                        operation,

                    "aggregation_field":
                        field,

                    "group_by":
                        None,

                    "preserved_source_row":
                        True,
                },
            )

        # ----------------------------------------------------
        # MEAN / SUM / MEDIAN / COUNT
        # ----------------------------------------------------

        result_value = calculate_value(
            input_table.rows
        )

        return ToolResult(
            columns=[
                "value"
            ],

            rows=[
                {
                    "value":
                        result_value
                }
            ],

            column_specs=[
                build_aggregate_value_spec(
                    input_table=input_table,
                    field=field,
                    operation=operation,
                )
            ],

            metadata={
                **input_table.metadata,

                "aggregation":
                    operation,

                "aggregation_field":
                    field,

                "group_by":
                    None,

                "preserved_source_row":
                    False,
            },
        )

    # ========================================================
    # 7. 分组
    # ========================================================

    groups = {}

    for row in input_table.rows:

        group_key = tuple(
            row.get(
                group_field
            )
            for group_field
            in group_fields
        )

        groups.setdefault(
            group_key,
            []
        ).append(
            row
        )

    result_rows = []

    # ========================================================
    # 8. MAX / MIN 分组
    #
    # 每组选择产生极值的完整 row
    # ========================================================

    if operation in {
        "max",
        "min",
    }:

        for group_rows in (
            groups.values()
        ):

            selected_row = (
                select_extreme_row(
                    group_rows
                )
            )

            if selected_row is None:
                continue

            result_rows.append(
                dict(
                    selected_row
                )
            )

        return ToolResult(
            columns=input_table.columns,

            rows=result_rows,
            column_specs=[
                spec.model_copy(
                    deep=True
                )
                for spec
                in input_table.column_specs
            ],
            metadata={
                **input_table.metadata,

                "aggregation":
                    operation,

                "aggregation_field":
                    field,

                "group_by":
                    group_fields,

                "preserved_source_row":
                    True,
            },
        )

    # ========================================================
    # 9. 其他分组聚合
    # ========================================================

    for (
        group_key,
        group_rows,
    ) in groups.items():

        result_row = {}

        for (
            index,
            group_field,
        ) in enumerate(
            group_fields
        ):

            result_row[
                group_field
            ] = group_key[
                index
            ]

        result_row[
            "value"
        ] = calculate_value(
            group_rows
        )

        result_rows.append(
            result_row
        )

    result_specs = []

    for group_field in group_fields:

        group_spec = copy_column_spec(
            input_table,
            group_field,
        )

        if group_spec is not None:
            result_specs.append(
                group_spec
            )

    result_specs.append(
        build_aggregate_value_spec(
            input_table=input_table,
            field=field,
            operation=operation,
        )
    )

    return ToolResult(
        columns=[
            *group_fields,
            "value",
        ],

        rows=result_rows,

        column_specs=result_specs,

        metadata={
            **input_table.metadata,

            "aggregation":
                operation,

            "aggregation_field":
                field,

            "group_by":
                group_fields,

            "preserved_source_row":
                False,
        },
    )

def sort_table(
    input_table: ToolResult,
    field: str,
    order: str = "ascending",
) -> ToolResult:
    """
    对任意 ToolResult 按指定字段排序。
    """

    if field not in input_table.columns:
        raise ValueError(
            f"排序字段不存在：{field}"
        )

    if order not in {
        "ascending",
        "descending",
    }:
        raise ValueError(
            f"未知排序方向：{order}"
        )

    reverse = (
        order == "descending"
    )

    # None 放到最后
    valid_rows = [
        row
        for row in input_table.rows
        if row.get(field) is not None
    ]

    none_rows = [
        row
        for row in input_table.rows
        if row.get(field) is None
    ]

    sorted_rows = sorted(
        valid_rows,
        key=lambda row: row[field],
        reverse=reverse,
    )

    sorted_rows.extend(
        none_rows
    )

    return ToolResult(
        columns=input_table.columns,

        rows=sorted_rows,

        column_specs=[
            spec.model_copy(
                deep=True
            )
            for spec
            in input_table.column_specs
        ],

        metadata={
            **input_table.metadata,

            "sorted_by":
                field,

            "sort_order":
                order,
        },
    )


def limit_table(
    input_table: ToolResult,
    limit: int,
) -> ToolResult:
    """
    保留任意 ToolResult 当前顺序中的前 N 行。

    本工具只负责截断，不负责排序。
    因此 Top-N / 前 N 名应先由 sort_table
    确定顺序，再调用 limit_table。
    """

    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
    ):
        raise TypeError(
            "limit 必须是整数。"
        )

    if limit <= 0:
        raise ValueError(
            "limit 必须大于 0。"
        )

    input_row_count = len(
        input_table.rows
    )

    limited_rows = list(
        input_table.rows[:limit]
    )

    return ToolResult(
        columns=list(
            input_table.columns
        ),

        rows=limited_rows,

        column_specs=[
            spec.model_copy(
                deep=True
            )
            for spec
            in input_table.column_specs
        ],

        metadata={
            **input_table.metadata,

            "limit":
                limit,

            "pre_limit_row_count":
                input_row_count,

            "post_limit_row_count":
                len(limited_rows),

            "truncated":
                input_row_count
                > limit,
        },
    )
