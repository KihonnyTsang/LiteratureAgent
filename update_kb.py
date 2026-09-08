from pathlib import Path

from app.database.sqlite_db import (
    init_db,
)

from app.ingestion.kb_sync import (
    sync_knowledge_base,
)

from app.ingestion.chunker import (
    build_chunks_for_all_pages,
)

from app.embedding.indexer import (
    build_vector_index,
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
)

PAPERS_FOLDER = (
    PROJECT_ROOT
    / "data"
    / "papers"
)


def main():

    print(
        "=" * 70
    )

    print(
        "Literature Agent - "
        "Knowledge Base Sync"
    )

    print(
        "=" * 70
    )

    # ========================================================
    # 1. DB schema
    # ========================================================

    print()
    print(
        "[1/4] 初始化数据库..."
    )

    init_db()

    # ========================================================
    # 2. Reconciliation
    # ========================================================

    print()
    print(
        "[2/4] 同步 PDF 与知识库..."
    )

    sync_result = (
        sync_knowledge_base(
            PAPERS_FOLDER
        )
    )

    # ========================================================
    # 3. Chunks
    # ========================================================

    print()
    print(
        "[3/4] 构建文本 Chunk..."
    )

    build_chunks_for_all_pages()

    # ========================================================
    # 4. Vector DB
    # ========================================================

    print()
    print(
        "[4/4] 更新向量知识库..."
    )

    build_vector_index()

    # ========================================================
    # Summary
    # ========================================================

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
        f"新增："
        f"{sync_result.new}"
    )

    print(
        f"修改："
        f"{sync_result.modified}"
    )

    print(
        f"删除："
        f"{sync_result.deleted}"
    )

    print(
        f"未变化："
        f"{sync_result.unchanged}"
    )

    if (
        sync_result.hash_backfilled
        > 0
    ):

        print(
            f"首次补写 Hash："
            f"{sync_result.hash_backfilled}"
        )

    print(
        "=" * 70
    )


if __name__ == "__main__":
    main()