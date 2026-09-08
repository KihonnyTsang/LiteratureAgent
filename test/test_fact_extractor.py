import pytest

from app.database.sqlite_db import (
    get_all_documents,
)

from app.extraction.fact_extractor import (
    extract_facts,
)


def find_document(
    title_fragment: str,
) -> dict:
    """
    从真实 KB 中定位测试论文。
    """

    documents = get_all_documents()

    document = next(
        (
            item
            for item
            in documents
            if title_fragment
            in item["title"]
        ),
        None,
    )

    assert (
        document
        is not None
    ), (
        "测试知识库中未找到论文："
        f"{title_fragment}"
    )

    return document


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.slow
def test_fact_extractor_power_density_positive() -> None:
    """
    Positive control：

    Siddiqui 论文包含作者报告的
    面积功率密度，应成功提取。
    """

    document = find_document(
        "Siddiqui"
    )

    facts = extract_facts(
        document_id=document["id"],
        metric="power_density",
        provenance_scope=(
            "author_results"
        ),
    )

    assert facts

    values = [
        fact.value
        for fact
        in facts
        if fact.value
        is not None
    ]

    assert values

    assert any(
        abs(
            float(value)
            - 13.5
        )
        < 1e-6
        for value
        in values
    )


@pytest.mark.integration
@pytest.mark.llm
@pytest.mark.slow
def test_fact_extractor_rejects_volumetric_power_density() -> None:
    """
    Negative control：

    Gong 文献中的 1.48 μW/cm³
    属于体积功率密度。

    对面积 power_density metric，
    Fact Extractor 不应返回该事实。
    """

    document = find_document(
        "Gong"
    )

    facts = extract_facts(
        document_id=document["id"],
        metric="power_density",
        provenance_scope=(
            "author_results"
        ),
    )

    assert (
        facts
        == []
    )