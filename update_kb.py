from app.ingestion.kb_manager import (
    update_knowledge_base,
)


def main() -> None:
    """
    CLI 入口。

    实际同步逻辑统一由
    app.ingestion.kb_manager
    提供。
    """

    print(
        "=" * 70
    )

    print(
        "LiteratureAgent - "
        "Knowledge Base Sync"
    )

    print(
        "=" * 70
    )

    result = (
        update_knowledge_base()
    )

    print()

    print(
        "=" * 70
    )

    print(
        "Knowledge Base Sync 完成"
    )

    print(
        "=" * 70
    )

    print(
        f"新增文献："
        f"{result.new_documents}"
    )

    print(
        f"修改文献："
        f"{result.modified_documents}"
    )

    print(
        f"删除文献："
        f"{result.deleted_documents}"
    )

    print(
        f"移动文献："
        f"{result.moved_documents}"
    )

    print(
        f"未变化文献："
        f"{result.unchanged_documents}"
    )

    if (
        result.hash_backfilled
        > 0
    ):

        print(
            f"首次补写 Hash："
            f"{result.hash_backfilled}"
        )

    print(
        f"本次新增 Chunks："
        f"{result.new_chunks}"
    )

    print(
        f"本次新增向量："
        f"{result.vectors_added}"
    )

    print(
        f"额外清理失效向量："
        f"{result.stale_vectors_deleted}"
    )

    print(
        "-" * 70
    )

    print(
        f"当前 PDF："
        f"{result.status.source_pdf_count}"
    )

    print(
        f"当前 Documents："
        f"{result.status.indexed_document_count}"
    )

    print(
        f"当前 Pages："
        f"{result.status.page_count}"
    )

    print(
        f"当前 Chunks："
        f"{result.status.chunk_count}"
    )

    print(
        f"当前 Vectors："
        f"{result.status.vector_count}"
    )

    print(
        f"仍需同步："
        f"{result.status.sync_required}"
    )

    print(
        "=" * 70
    )


if __name__ == "__main__":
    main()