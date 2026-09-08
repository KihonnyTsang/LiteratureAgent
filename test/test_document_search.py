import pytest

from app.database.sqlite_db import (
    get_all_documents,
)

from app.rag.retriever import (
    semantic_search_in_document,
)


@pytest.mark.integration
@pytest.mark.slow
def test_document_scoped_semantic_search() -> None:
    """
    验证每篇论文都可以执行
    document-scoped semantic retrieval。

    使用真实：

    - SQLite
    - Qdrant
    - BGE-M3

    不调用 LLM。
    """

    documents = get_all_documents()

    assert documents

    query = (
        "What is the maximum output power density "
        "reported for the device? "
        "Peak output power density, power density, "
        "maximum power under load resistance."
    )

    for document in documents:

        results = (
            semantic_search_in_document(
                query=query,
                document_id=(
                    document["id"]
                ),
                top_k=8,
            )
        )

        assert (
            results
        ), (
            "文档检索结果为空："
            f"{document['title']}"
        )

        assert (
            len(results)
            <= 8
        )

        for result in results:

            assert (
                result["text"]
                .strip()
            )

            assert (
                result["page_number"]
                is not None
            )

            assert (
                result["score"]
                is not None
            )