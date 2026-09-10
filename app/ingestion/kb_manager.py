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
    deduplicate_disk_documents,
    scan_papers_folder,
    sync_knowledge_base,
)
from app.vectorstore.vector_store import (
    get_all_point_ids,
    get_qdrant_client,
    init_collection,
)

from app.config import (
    get_papers_folder,
)

PAPERS_FOLDER = (
    get_papers_folder()
)

_SYNC_LOCK = Lock()


from app.enrichment.sync_pipeline import (
    update_structured_knowledge,
)


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
    pending_moved: int
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
    moved_documents: int
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
    检查当前 PDF Library、SQLite 和 Qdrant
    的知识库生命周期状态。

    状态语义与 sync_knowledge_base 一致：

    same path + same hash
        -> UNCHANGED

    same path + different hash
        -> MODIFIED

    different path + unique same hash
        -> MOVED

    unmatched disk
        -> NEW

    unmatched database
        -> DELETED

    exact duplicate physical PDFs
    会先按 content_hash 折叠为逻辑唯一文档。
    """

    init_db()

    # ========================================================
    # 1. Physical PDF Library
    # ========================================================

    raw_disk_documents = (
        scan_papers_folder(
            PAPERS_FOLDER
        )
    )

    # ========================================================
    # 2. Exact-content deduplication
    # ========================================================

    (
        disk_documents,
        _duplicate_groups,
    ) = deduplicate_disk_documents(
        raw_disk_documents
    )

    # ========================================================
    # 3. SQLite documents
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
    # 4. Same path:
    #
    # UNCHANGED / MODIFIED / hash backfill
    # ========================================================

    common_paths = (
        disk_paths
        & database_paths
    )

    pending_modified = 0
    pending_hash_backfill = 0

    for local_path in sorted(
        common_paths
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

            continue

        if (
            database_hash
            != disk_hash
        ):

            pending_modified += 1

    # ========================================================
    # 5. Different paths:
    #
    # may be MOVED
    # ========================================================

    unmatched_database_paths = (
        database_paths
        - disk_paths
    )

    unmatched_disk_paths = (
        disk_paths
        - database_paths
    )

    # ========================================================
    # 6. Build hash buckets
    # ========================================================

    database_hash_buckets: dict[
        str,
        list[str],
    ] = {}

    for local_path in (
        unmatched_database_paths
    ):

        document = (
            database_documents[
                local_path
            ]
        )

        content_hash = (
            document.get(
                "content_hash"
            )
        )

        if not content_hash:

            continue

        database_hash_buckets.setdefault(
            content_hash,
            [],
        ).append(
            local_path
        )

    disk_hash_buckets: dict[
        str,
        list[str],
    ] = {}

    for local_path in (
        unmatched_disk_paths
    ):

        document = (
            disk_documents[
                local_path
            ]
        )

        content_hash = (
            document.get(
                "content_hash"
            )
        )

        if not content_hash:

            continue

        disk_hash_buckets.setdefault(
            content_hash,
            [],
        ).append(
            local_path
        )

    # ========================================================
    # 7. MOVED
    #
    # 只有双方 hash 都唯一时才自动认定为 MOVED。
    # duplicate ambiguity 不做猜测。
    # ========================================================

    moved_database_paths: set[
        str
    ] = set()

    moved_disk_paths: set[
        str
    ] = set()

    shared_hashes = (
        set(
            database_hash_buckets
        )
        & set(
            disk_hash_buckets
        )
    )

    for content_hash in sorted(
        shared_hashes
    ):

        old_paths = (
            database_hash_buckets[
                content_hash
            ]
        )

        new_paths = (
            disk_hash_buckets[
                content_hash
            ]
        )

        if (
            len(old_paths) != 1
            or len(new_paths) != 1
        ):

            continue

        moved_database_paths.add(
            old_paths[0]
        )

        moved_disk_paths.add(
            new_paths[0]
        )

    pending_moved = len(
        moved_database_paths
    )

    # ========================================================
    # 8. NEW / DELETED
    #
    # MOVED 两侧必须排除。
    # ========================================================

    pending_deleted = len(
        unmatched_database_paths
        - moved_database_paths
    )

    pending_new = len(
        unmatched_disk_paths
        - moved_disk_paths
    )

    # ========================================================
    # 9. SQLite counts
    # ========================================================

    (
        indexed_document_count,
        page_count,
        chunk_count,
        pages_without_chunks,
    ) = _get_sqlite_counts()

    # ========================================================
    # 10. Qdrant
    # ========================================================

    vector_count = (
        _get_vector_count()
    )

    # ========================================================
    # 11. Sync required
    # ========================================================

    sync_required = any(
        (
            pending_new,
            pending_modified,
            pending_deleted,
            pending_moved,
            pending_hash_backfill,
            pages_without_chunks,
            (
                chunk_count
                != vector_count
            ),
        )
    )

    return KnowledgeBaseStatus(
        # 物理 PDF 数，包括 exact duplicates。
        source_pdf_count=(
            len(
                raw_disk_documents
            )
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

        pending_moved=(
            pending_moved
        ),

        pending_hash_backfill=(
            pending_hash_backfill
        ),

        sync_required=(
            sync_required
        ),
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

    同步完成后执行确定性的结构化知识更新：

    Numeric Mentions
    -> Unit Signatures
    -> Metric Classification
    -> Deterministic Provenance
    -> Materialized Facts

    不执行 Semantic Provenance。
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
        # 5. Deterministic structured enrichment
        # ====================================================

        update_structured_knowledge()

        # ====================================================
        # 6. Final status
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

                moved_documents=(
                    sync_result.moved
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
