from app.agent.answer_renderer import (
    format_column_value,
)

from app.agent.answer_schemas import (
    AnswerColumn,
)


def build_measure_column() -> AnswerColumn:

    return AnswerColumn(
        field="value",
        label="测试指标",
        role="measure",
        visible=True,
        format_hint="number",
        unit_field="unit",
    )


def build_raw_measure_column() -> AnswerColumn:

    return AnswerColumn(
        field="raw_value",
        label="原始测试指标",
        role="raw_measure",
        visible=True,
        format_hint="number",
        unit_field="raw_unit",
    )


def test_scientific_value_renderer():

    measure_column = (
        build_measure_column()
    )

    raw_measure_column = (
        build_raw_measure_column()
    )

    # ========================================================
    # Scalar
    # ========================================================

    scalar_row = {
        "value_type": "scalar",

        "value": 10.1,
        "value_min": None,
        "value_max": None,
        "unit": "pC/N",

        "raw_value": 10.1,
        "raw_value_min": None,
        "raw_value_max": None,
        "raw_unit": "pC/N",
    }

    assert (
        format_column_value(
            scalar_row,
            measure_column,
        )
        == "10.1 pC/N"
    )

    # ========================================================
    # Range
    # ========================================================

    range_row = {
        "value_type": "range",

        "value": None,
        "value_min": 120.0,
        "value_max": 960.0,
        "unit": "pC/N",

        "raw_value": None,
        "raw_value_min": 120.0,
        "raw_value_max": 960.0,
        "raw_unit": "pC/N",
    }

    assert (
        format_column_value(
            range_row,
            measure_column,
        )
        == "120–960 pC/N"
    )

    assert (
        format_column_value(
            range_row,
            raw_measure_column,
        )
        == "120–960 pC/N"
    )

    # ========================================================
    # Lower Bound
    # ========================================================

    lower_bound_row = {
        "value_type":
            "lower_bound",

        "value": 500.0,
        "value_min": None,
        "value_max": None,
        "unit": "MV/m",
    }

    assert (
        format_column_value(
            lower_bound_row,
            measure_column,
        )
        == "> 500 MV/m"
    )

    # ========================================================
    # Upper Bound
    # ========================================================

    upper_bound_row = {
        "value_type":
            "upper_bound",

        "value": 80.0,
        "value_min": None,
        "value_max": None,
        "unit": "°C",
    }

    assert (
        format_column_value(
            upper_bound_row,
            measure_column,
        )
        == "< 80 °C"
    )

    print(
        "Scientific Value Renderer Tests Passed"
    )


if __name__ == "__main__":
    test_scientific_value_renderer()
