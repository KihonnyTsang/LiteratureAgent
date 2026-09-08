from app.rag.qa import (
    answer_question,
)

from app.tools.schemas import (
    SourceRef,
    TextResult,
)


def rag_search(
    question: str,
    top_k: int = 5,
) -> TextResult:
    """
    基于本地文献知识库执行 grounded RAG QA。

    该 Tool 复用已有的：

    answer_question()

    工作流程：

    semantic_search
        ↓
    retrieve chunks
        ↓
    grounded LLM answer
        ↓
    cited sources
        ↓
    TextResult

    注意：

    这里不重新实现 Retriever，
    也不重新实现 RAG Prompt。
    """

    if not question.strip():

        raise ValueError(
            "rag_search 的 question 不能为空。"
        )

    if top_k <= 0:

        raise ValueError(
            "rag_search 的 top_k "
            "必须大于 0。"
        )

    result = answer_question(
        question=question,
        top_k=top_k,
    )

    answer = result.get(
        "answer",
        "",
    )

    raw_sources = result.get(
        "sources",
        [],
    )

    sources = []

    for source in raw_sources:

        sources.append(
            SourceRef(
                source_id=(
                    source["source_id"]
                ),

                title=(
                    source["title"]
                ),

                page_number=(
                    source.get(
                        "page_number"
                    )
                ),

                chunk_index=(
                    source.get(
                        "chunk_index"
                    )
                ),

                filename=(
                    source.get(
                        "filename"
                    )
                ),

                local_path=(
                    source.get(
                        "local_path"
                    )
                ),

                score=(
                    source.get(
                        "score"
                    )
                ),
            )
        )

    return TextResult(
        text=answer,

        sources=sources,

        metadata={
            "result_kind":
                "grounded_text",

            "grounded":
                True,

            "retrieval_top_k":
                top_k,

            "source_count":
                len(sources),
        },
    )