from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from app.database.sqlite_db import (
    get_connection,
    get_documents_for_sync,
    init_db,
)
from app.embedding.indexer import (
    build_vector_index,
)
from app.ingestion.chunker import (
    build_chunks_for_all_pages,
)
from app.ingestion.kb_sync import (
    scan_papers_folder,
    sync_knowledge_base,
)
from app.vectorstore.vector_store import (
    get_all_point_ids,
    get_qdrant_client,
    init_collection,
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

PAPERS_FOLDER = (
    PROJECT_ROOT
    / "data"
    / "papers"
)

_SYNC_LOCK = Lock()


class KnowledgeBaseSyncInProgressError(
    RuntimeError
):
    """
    已有知识库同步任务正在执行。
    """


@dataclass(frozen=True)
class KnowledgeBaseStatus:
    """
    知识库当前状态。

    这里只描述数据生命周期状态，
    不调用 LLM，也不加载 Embedding 模型。
    """

    source_pdf_count: int
    indexed_document_count: int
    page_count: int
    chunk_count: int
    vector_count: int
    pages_without_chunks: int

    pending_new: int
    pending_modified: int
    pending_deleted: int
    pending_hash_backfill: int

    sync_required: bool


@dataclass(frozen=True)
class KnowledgeBaseUpdateResult:
    """
    一次完整知识库更新的结果。
    """

    new_documents: int
    modified_documents: int
    deleted_documents: int
    unchanged_documents: int
    hash_backfilled: int

    new_chunks: int

    vector_sqlite_count: int
    vector_qdrant_count_before: int
    vectors_added: int
    stale_vectors_deleted: int
    vectors_unchanged: int

    status: KnowledgeBaseStatus


def _get_sqlite_counts(
) -> tuple[int, int, int, int]:
    """
    获取知识库核心 SQLite 计数。

    返回：

    documents
    pages
    chunks
    pages_without_chunks
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM documents"
        )

        document_count = int(
            cursor.fetchone()[0]
        )

        cursor.execute(
            "SELECT COUNT(*) FROM pages"
        )

        page_count = int(
            cursor.fetchone()[0]
        )

        cursor.execute(
            "SELECT COUNT(*) FROM chunks"
        )

        chunk_count = int(
            cursor.fetchone()[0]
        )

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM pages AS p
            WHERE
                TRIM(
                    COALESCE(p.text, '')
                ) <> ''
                AND NOT EXISTS (
                    SELECT 1
                    FROM chunks AS c
                    WHERE
                        c.document_id = p.document_id
                        AND c.page_number = p.page_number
                )
            """
        )

        pages_without_chunks = int(
            cursor.fetchone()[0]
        )

        return (
            document_count,
            page_count,
            chunk_count,
            pages_without_chunks,
        )

    finally:

        connection.close()


def _get_vector_count() -> int:
    """
    读取 Qdrant 当前 Point 数量。

    不计算新的 Embedding。
    """

    init_collection()

    client = (
        get_qdrant_client()
    )

    try:

        return len(
            get_all_point_ids(
                client
            )
        )

    finally:

        client.close()


def get_knowledge_base_status(
) -> KnowledgeBaseStatus:
    """
    检查：

    data/papers
    SQLite
    Qdrant

    当前状态。

    这里只检测，不执行同步。
    """

    init_db()

    # ========================================================
    # 1. data/papers
    # ========================================================

    disk_documents = (
        scan_papers_folder(
            PAPERS_FOLDER
        )
    )

    # ========================================================
    # 2. SQLite documents
    # ========================================================

    database_documents = {
        document["local_path"]:
            document
        for document
        in get_documents_for_sync()
    }

    disk_paths = set(
        disk_documents
    )

    database_paths = set(
        database_documents
    )

    # ========================================================
    # 3. NEW / DELETED
    # ========================================================

    pending_new = len(
        disk_paths
        - database_paths
    )

    pending_deleted = len(
        database_paths
        - disk_paths
    )

    # ========================================================
    # 4. MODIFIED / legacy hash
    # ========================================================

    pending_modified = 0

    pending_hash_backfill = 0

    for local_path in (
        disk_paths
        & database_paths
    ):

        disk_hash = (
            disk_documents[
                local_path
            ][
                "content_hash"
            ]
        )

        database_hash = (
            database_documents[
                local_path
            ].get(
                "content_hash"
            )
        )

        if not database_hash:

            pending_hash_backfill += 1

        elif (
            database_hash
            != disk_hash
        ):

            pending_modified += 1

    # ========================================================
    # 5. SQLite counts
    # ========================================================

    (
        indexed_document_count,
        page_count,
        chunk_count,
        pages_without_chunks,
    ) = _get_sqlite_counts()

    # ========================================================
    # 6. Qdrant
    # ========================================================

    vector_count = (
        _get_vector_count()
    )

    # ========================================================
    # 7. 是否需要同步
    # ========================================================

    sync_required = any(
        (
            pending_new,
            pending_modified,
            pending_deleted,
            pending_hash_backfill,
            pages_without_chunks,
            (
                chunk_count
                != vector_count
            ),
        )
    )

    return KnowledgeBaseStatus(
        source_pdf_count=(
            len(disk_documents)
        ),

        indexed_document_count=(
            indexed_document_count
        ),

        page_count=page_count,

        chunk_count=chunk_count,

        vector_count=vector_count,

        pages_without_chunks=(
            pages_without_chunks
        ),

        pending_new=pending_new,

        pending_modified=(
            pending_modified
        ),

        pending_deleted=(
            pending_deleted
        ),

        pending_hash_backfill=(
            pending_hash_backfill
        ),

        sync_required=sync_required,
    )


def update_knowledge_base(
) -> KnowledgeBaseUpdateResult:
    """
    执行一次完整、确定性的知识库更新。

    唯一 pipeline：

    data/papers
        ↓
    SQLite reconciliation
        ↓
    missing chunks
        ↓
    Qdrant reconciliation

    不执行 Fact Extraction。

    不调用 LLM。
    """

    acquired = (
        _SYNC_LOCK.acquire(
            blocking=False
        )
    )

    if not acquired:

        raise (
            KnowledgeBaseSyncInProgressError(
                "知识库同步正在执行，"
                "请稍后再试。"
            )
        )

    try:

        # ====================================================
        # 1. DB
        # ====================================================

        init_db()

        # ====================================================
        # 2. PDF reconciliation
        # ====================================================

        sync_result = (
            sync_knowledge_base(
                PAPERS_FOLDER
            )
        )

        # ====================================================
        # 3. Chunk
        # ====================================================

        new_chunks = (
            build_chunks_for_all_pages()
        )

        # ====================================================
        # 4. Vector reconciliation
        # ====================================================

        vector_result = (
            build_vector_index()
        )

        # ====================================================
        # 5. Final status
        # ====================================================

        status = (
            get_knowledge_base_status()
        )

        return (
            KnowledgeBaseUpdateResult(
                new_documents=(
                    sync_result.new
                ),

                modified_documents=(
                    sync_result.modified
                ),

                deleted_documents=(
                    sync_result.deleted
                ),

                unchanged_documents=(
                    sync_result.unchanged
                ),

                hash_backfilled=(
                    sync_result
                    .hash_backfilled
                ),

                new_chunks=(
                    new_chunks
                ),

                vector_sqlite_count=(
                    vector_result
                    .sqlite_count
                ),

                vector_qdrant_count_before=(
                    vector_result
                    .qdrant_count_before
                ),

                vectors_added=(
                    vector_result
                    .added_count
                ),

                stale_vectors_deleted=(
                    vector_result
                    .deleted_count
                ),

                vectors_unchanged=(
                    vector_result
                    .unchanged_count
                ),

                status=status,
            )
        )

    finally:

        _SYNC_LOCK.release()