import pytest

from app.tools.fact_tool import (
    query_facts,
)


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.slow
def test_gong_volumetric_power_density_is_excluded() -> None:
    """
    真实知识库语义边界测试。

    Gong 2018 报告的是：

        1.48 μW/cm³

    这是体积功率密度。

    当前 power_density metric
    定义的是面积功率密度，
    因此 Gong 不应进入该 Fact 集合。

    注意：

    Pint 的物理量纲拒绝能力已经由
    test_unit_dimensionality_guard.py
    单独测试。

    本测试只负责 Semantic Guard。
    """

    result = query_facts(
        metric="power_density",
        scope="all_documents",
        provenance_scope=(
            "author_results"
        ),
    )

    gong_rows = [
        row
        for row
        in result.rows
        if "Gong"
        in row.get(
            "title",
            "",
        )
    ]

    assert (
        not gong_rows
    ), (
        "Gong 的体积功率密度"
        "错误进入了面积 "
        "power_density Fact rows。"
    )