import pytest

from app.tools.fact_tool import (
    query_facts,
)


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.slow
def test_power_density_fact_tool() -> None:
    """
    验证 power_density Fact Tool。

    重点测试：

    - author_results scope
    - all_documents scope
    - 标准化面积功率密度
    - 多篇论文可比较
    - 不混入 Gong 的体积功率密度

    如果 extraction cache 已存在，
    通常直接读取 SQLite。

    如果 cache 缺失，
    query_facts 可能触发真实抽取，
    因此仍标记 llm + slow。
    """

    result = query_facts(
        metric="power_density",
        scope="all_documents",
        provenance_scope=(
            "author_results"
        ),
    )

    assert result.rows

    # ========================================================
    # Comparable rows
    # ========================================================

    comparable_rows = [
        row
        for row
        in result.rows
        if row.get("value")
        is not None
    ]

    assert comparable_rows

    assert all(
        row.get("unit")
        == "W/m²"
        for row
        in comparable_rows
    )

    # ========================================================
    # Expected documents
    # ========================================================

    titles = {
        row.get(
            "title",
            "",
        )
        for row
        in comparable_rows
    }

    for expected_title in [
        "Siddiqui",
        "Si",
        "Rana",
        "Kim",
        "Zhang",
    ]:

        assert any(
            expected_title
            in title
            for title
            in titles
        )

    # ========================================================
    # Known positive value
    # ========================================================

    siddiqui_rows = [
        row
        for row
        in comparable_rows
        if "Siddiqui"
        in row.get(
            "title",
            "",
        )
    ]

    assert siddiqui_rows

    assert any(
        abs(
            float(
                row["value"]
            )
            - 135.0
        )
        < 1e-9
        for row
        in siddiqui_rows
    )