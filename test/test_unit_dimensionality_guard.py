import math

import pytest

from app.extraction.schemas import (
    ExtractedFact,
    MetricSpec,
)

from app.extraction.unit_normalizer import (
    normalize_fact,
)

from app.tools.fact_tool import (
    fact_to_row,
)


def build_power_density_metric() -> MetricSpec:
    """
    面功率密度 Metric。

    canonical unit:
        W/m²
    """

    return MetricSpec(
        key="power_density",
        display_name="输出功率密度",
        description=(
            "单位面积上的输出功率密度。"
        ),
        search_queries=[
            "power density",
            "output power density",
        ],
        canonical_unit="W/m²",
        valid_units=[
            "W/m²",
            "mW/cm²",
            "μW/cm²",
        ],
        exclude_terms=[],
    )


@pytest.fixture
def metric() -> MetricSpec:
    """
    pytest 使用的面积功率密度 Metric fixture。
    """

    return build_power_density_metric()

def build_fact(
    value: float,
    unit: str,
    evidence: str,
) -> ExtractedFact:
    """
    构造 synthetic scientific fact。
    """

    return ExtractedFact(
        document_id="doc_test",
        metric_name="power_density",

        value_type="scalar",

        value=value,
        value_min=None,
        value_max=None,

        unit=unit,

        page_number=1,
        chunk_id=1,

        evidence=evidence,
        evidence_verified=True,

        condition_text=None,

        provenance="author_result",

        confidence=1.0,
    )


def test_positive_control(
    metric: MetricSpec,
) -> None:
    """
    Positive Control:

    13.5 mW/cm²
        ->
    135 W/m²

    这是同一物理量纲：
        power / area
    """

    fact = build_fact(
        value=13.5,
        unit="mW/cm²",
        evidence=(
            "The highest power density "
            "was 13.5 mW/cm2."
        ),
    )

    normalized = normalize_fact(
        fact,
        metric,
    )

    print()
    print(
        "=" * 80
    )
    print(
        "Positive Control"
    )
    print(
        "=" * 80
    )

    print(
        "converted:",
        normalized.converted,
    )
    print(
        "value:",
        normalized.value,
    )
    print(
        "unit:",
        normalized.unit,
    )
    print(
        "error:",
        normalized.error,
    )

    assert (
        normalized.converted
        is True
    )

    assert math.isclose(
        normalized.value,
        135.0,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    assert (
        normalized.unit
        == "W/m²"
    )

    assert (
        normalized.error
        is None
    )

    # --------------------------------------------------------
    # 再检查 Fact Tool 输出
    # --------------------------------------------------------

    row = fact_to_row(
        document={
            "id": "doc_test",
            "title": (
                "Positive Control Paper"
            ),
        },
        fact=fact,
        metric_spec=metric,
    )

    assert math.isclose(
        row["value"],
        135.0,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )

    assert (
        row["unit"]
        == "W/m²"
    )

    assert (
        row["raw_value"]
        == 13.5
    )

    assert (
        row["raw_unit"]
        == "mW/cm²"
    )

    assert (
        row["normalization_error"]
        is None
    )


def test_negative_control(
    metric: MetricSpec,
) -> None:
    """
    Negative Control:

    1.48 μW/cm³
        -X->
    W/m²

    两者量纲不同：

        power / volume
        !=
        power / area

    Unit Normalizer 必须拒绝转换。

    Fact Tool 还必须进一步保证：
    该原始数据不能暴露成可比较 value。
    """

    fact = build_fact(
        value=1.48,
        unit="μW/cm³",
        evidence=(
            "a power density of "
            "1.48 μW cm−3"
        ),
    )

    normalized = normalize_fact(
        fact,
        metric,
    )

    print()
    print(
        "=" * 80
    )
    print(
        "Negative Control"
    )
    print(
        "=" * 80
    )

    print(
        "converted:",
        normalized.converted,
    )
    print(
        "returned value:",
        normalized.value,
    )
    print(
        "returned unit:",
        normalized.unit,
    )
    print(
        "error:",
        normalized.error,
    )

    # ========================================================
    # 第一层：
    # Pint / Unit Normalizer 必须拒绝
    # ========================================================

    assert (
        normalized.converted
        is False
    )

    assert (
        normalized.error
        is not None
    )

    # 注意：
    #
    # 当前 normalize_fact 的 contract
    # 是转换失败时保留原始值。
    #
    # 所以这里不应该断言：
    #
    # normalized.value is None
    #
    # 而应该验证它没有被伪装成
    # canonical-unit 数据。
    assert (
        normalized.value
        == 1.48
    )

    assert (
        normalized.unit
        == "μW/cm³"
    )

    # ========================================================
    # 第二层：
    # Fact Tool 必须清空 comparable fields
    # ========================================================

    row = fact_to_row(
        document={
            "id": "doc_gong_test",
            "title": (
                "Gong dimensionality "
                "negative control"
            ),
        },
        fact=fact,
        metric_spec=metric,
    )

    print()
    print(
        "Fact Tool row:"
    )

    print(
        "value:",
        row["value"],
    )

    print(
        "unit:",
        row["unit"],
    )

    print(
        "raw_value:",
        row["raw_value"],
    )

    print(
        "raw_unit:",
        row["raw_unit"],
    )

    print(
        "normalization_error:",
        row[
            "normalization_error"
        ],
    )

    # --------------------------------------------------------
    # Comparable normalized data 必须不存在
    # --------------------------------------------------------

    assert (
        row["value"]
        is None
    )

    assert (
        row["value_min"]
        is None
    )

    assert (
        row["value_max"]
        is None
    )

    assert (
        row["unit"]
        is None
    )

    # --------------------------------------------------------
    # 原始科研事实必须完整保留
    # --------------------------------------------------------

    assert (
        row["raw_value"]
        == 1.48
    )

    assert (
        row["raw_unit"]
        == "μW/cm³"
    )

    assert (
        row["normalization_error"]
    )


def main():

    metric = (
        build_power_density_metric()
    )

    test_positive_control(
        metric
    )

    test_negative_control(
        metric
    )

    print()
    print(
        "=" * 80
    )

    print(
        "Unit Dimensionality Guard "
        "Tests Passed"
    )

    print(
        "=" * 80
    )


if __name__ == "__main__":
    main()