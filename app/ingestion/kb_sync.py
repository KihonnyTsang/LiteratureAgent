from dataclasses import dataclass
from pathlib import Path

from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
)

from app.database.sqlite_db import (
    delete_document_data,
    get_documents_for_sync,
    update_document_content_hash,
    update_document_local_path,
)

from app.ingestion.ingest import (
    calculate_file_hash,
    ingest_pdf,
)

from app.vectorstore.vector_store import (
    COLLECTION_NAME,
    get_qdrant_client,
    init_collection,
)


@dataclass
class SyncResult:
    new: int = 0
    modified: int = 0
    deleted: int = 0
    moved: int = 0
    unchanged: int = 0
    hash_backfilled: int = 0


def scan_papers_folder(
    folder: Path,
) -> dict[str, dict]:
    """
    递归扫描 PDF 根目录中的所有 PDF。

    key:
        resolve 后的绝对 local_path

    value:
        path
        filename
        content_hash

    不会静默创建用户配置的目录。

    如果目录不存在，直接报错，
    避免因为路径拼写错误而把现有知识库
    误判为全部 DELETED。
    """

    folder = folder.resolve()

    if not folder.exists():

        raise FileNotFoundError(
            "PDF 根目录不存在："
            f"{folder}"
        )

    if not folder.is_dir():

        raise NotADirectoryError(
            "PDF 根路径不是目录："
            f"{folder}"
        )

    result = {}

    pdf_files = sorted(
        (
            path
            for path
            in folder.rglob("*")
            if (
                path.is_file()
                and path.suffix.lower()
                == ".pdf"
            )
        ),
        key=lambda path: str(
            path
        ),
    )

    for pdf_path in pdf_files:

        resolved = (
            pdf_path.resolve()
        )

        local_path = str(
            resolved
        )

        result[
            local_path
        ] = {
            "path":
                resolved,

            "filename":
                resolved.name,

            "content_hash":
                calculate_file_hash(
                    resolved
                ),
        }

    return result

def deduplicate_disk_documents(
    disk_documents: dict[str, dict],
) -> tuple[
    dict[str, dict],
    dict[str, list[str]],
]:
    """
    按 content_hash 折叠字节级完全相同的 PDF。

    返回：

    unique_documents:
        用于知识库 reconciliation 的逻辑文档。

    duplicate_groups:
        {
            content_hash: [
                path_1,
                path_2,
                ...
            ]
        }

    canonical path 的选择规则：

        对相同 content_hash 的所有绝对路径
        做字符串排序，选择第一条。

    这个规则：
    - 确定性
    - 与 Zotero 无关
    - 与文件名无关
    - 不使用业务 hardcoding
    """

    hash_buckets: dict[
        str,
        list[str],
    ] = {}

    documents_without_hash = []

    for (
        local_path,
        document,
    ) in disk_documents.items():

        content_hash = (
            document.get(
                "content_hash"
            )
        )

        if not content_hash:

            documents_without_hash.append(
                local_path
            )

            continue

        hash_buckets.setdefault(
            content_hash,
            [],
        ).append(
            local_path
        )

    unique_documents: dict[
        str,
        dict,
    ] = {}

    duplicate_groups: dict[
        str,
        list[str],
    ] = {}

    for (
        content_hash,
        paths,
    ) in hash_buckets.items():

        sorted_paths = sorted(
            paths
        )

        canonical_path = (
            sorted_paths[0]
        )

        unique_documents[
            canonical_path
        ] = (
            disk_documents[
                canonical_path
            ]
        )

        if len(sorted_paths) > 1:

            duplicate_groups[
                content_hash
            ] = sorted_paths

    # scan_papers_folder 正常情况下
    # 每个 PDF 都一定有 hash。
    #
    # 这里仍然保留 defensive fallback，
    # 避免未来 scanner contract 改变时
    # 静默丢失文件。
    for local_path in sorted(
        documents_without_hash
    ):

        unique_documents[
            local_path
        ] = (
            disk_documents[
                local_path
            ]
        )

    return (
        unique_documents,
        duplicate_groups,
    )


def delete_document_vectors(
    document_id: str,
) -> None:
    """
    从 Qdrant 删除某篇文献的全部向量。

    Qdrant payload 已经包含 document_id，
    因此可以按 document_id 过滤删除。
    """

    init_collection()

    client = (
        get_qdrant_client()
    )

    try:

        client.delete(
            collection_name=(
                COLLECTION_NAME
            ),

            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",

                        match=MatchValue(
                            value=document_id
                        ),
                    )
                ]
            ),

            wait=True,
        )

    finally:

        client.close()

def update_document_vector_local_path(
    document_id: str,
    local_path: str,
) -> None:
    """
    更新 Qdrant 中某篇文献已有 Points 的
    local_path payload。

    只修改 metadata：

        local_path

    不修改：
    - point id
    - vector
    - text
    - title
    - filename
    - chunk metadata

    用于 PDF relocation。
    """

    init_collection()

    client = (
        get_qdrant_client()
    )

    try:

        client.set_payload(
            collection_name=(
                COLLECTION_NAME
            ),

            payload={
                "local_path":
                    local_path,
            },

            points=Filter(
                must=[
                    FieldCondition(
                        key="document_id",

                        match=MatchValue(
                            value=document_id
                        ),
                    )
                ]
            ),

            wait=True,
        )

    finally:

        client.close()

def remove_document(
    document: dict,
) -> None:
    """
    删除一个文档的全部派生状态。

    顺序：

    1. Qdrant
    2. SQLite facts / extraction_runs
    3. SQLite document
       -> pages/chunks cascade
    """

    document_id = (
        document["id"]
    )

    print(
        f"清理旧知识："
        f"{document['filename']}"
    )

    delete_document_vectors(
        document_id
    )

    delete_document_data(
        document_id
    )


def sync_knowledge_base(
    papers_folder: Path,
) -> SyncResult:
    """
    将配置的 PDF Library
    视为知识库 source of truth。

    自动识别：

    NEW
    MODIFIED
    DELETED
    MOVED
    UNCHANGED

    MOVED 定义：

        local_path 不同
        但 content_hash 完全相同

    MOVED 不重新：
    - parse PDF
    - build chunks
    - embedding
    - extraction

    只更新 documents.local_path。
    """

    result = SyncResult()

    # ========================================================
    # 1. 当前磁盘状态
    # ========================================================

    raw_disk_documents = (
        scan_papers_folder(
            papers_folder
        )
    )

    (
        disk_documents,
        duplicate_groups,
    ) = deduplicate_disk_documents(
        raw_disk_documents
    )

    if duplicate_groups:

        skipped_duplicate_count = sum(
            len(paths) - 1
            for paths
            in duplicate_groups.values()
        )

        print()

        print(
            "[DUPLICATE] "
            f"检测到 "
            f"{skipped_duplicate_count} "
            "个完全重复 PDF，"
            "不会重复入库。"
        )

        for paths in (
                duplicate_groups.values()
        ):

            canonical_path = (
                paths[0]
            )

            print(
                "  保留："
                f"{canonical_path}"
            )

            for duplicate_path in (
                    paths[1:]
            ):
                print(
                    "  跳过："
                    f"{duplicate_path}"
                )

    # ========================================================
    # 2. 当前 SQLite 状态
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
    # 3. 路径仍然相同的文档
    # ========================================================

    common_paths = (
        disk_paths
        & database_paths
    )

    modified_paths = []

    for local_path in sorted(
        common_paths
    ):

        disk_document = (
            disk_documents[
                local_path
            ]
        )

        database_document = (
            database_documents[
                local_path
            ]
        )

        disk_hash = (
            disk_document[
                "content_hash"
            ]
        )

        database_hash = (
            database_document.get(
                "content_hash"
            )
        )

        # ----------------------------------------------------
        # Legacy database hash backfill
        # ----------------------------------------------------

        if not database_hash:

            update_document_content_hash(
                document_id=(
                    database_document[
                        "id"
                    ]
                ),

                content_hash=(
                    disk_hash
                ),
            )

            result.hash_backfilled += 1
            result.unchanged += 1

            print(
                "[BASELINE] "
                f"{database_document['filename']} "
                "补写 content hash"
            )

            continue

        # ----------------------------------------------------
        # UNCHANGED
        # ----------------------------------------------------

        if (
            database_hash
            == disk_hash
        ):

            result.unchanged += 1

            print(
                "[UNCHANGED] "
                f"{database_document['filename']}"
            )

            continue

        # ----------------------------------------------------
        # MODIFIED
        # ----------------------------------------------------

        print()

        print(
            "[MODIFIED] "
            f"{database_document['filename']}"
        )

        remove_document(
            database_document
        )

        modified_paths.append(
            local_path
        )

        result.modified += 1

    # ========================================================
    # 4. 路径消失 / 新出现
    #
    # 先不要直接认为是：
    #
    # DELETED / NEW
    #
    # 因为它可能只是被移动了。
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
    # 5. 为 unmatched 文档建立 hash buckets
    # ========================================================

    database_hash_buckets = {}

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

    disk_hash_buckets = {}

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
    # 6. MOVED detection
    #
    # 只有 hash 在 DB 与磁盘两侧都唯一时，
    # 才自动认定为 MOVED。
    #
    # 如果存在重复 PDF：
    #
    # hash -> 多个路径
    #
    # 不进行猜测。
    # ========================================================

    moved_database_paths = set()
    moved_disk_paths = set()

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

        old_path = old_paths[0]
        new_path = new_paths[0]

        database_document = (
            database_documents[
                old_path
            ]
        )

        disk_document = (
            disk_documents[
                new_path
            ]
        )

        document_id = (
            database_document[
                "id"
            ]
        )

        # ----------------------------------------------------
        # 先更新 Qdrant payload
        #
        # 顺序故意是：
        #
        # Qdrant -> SQLite
        #
        # 如果 Qdrant 成功但 SQLite 失败，
        # 下次 sync 仍然会再次识别为 MOVED，
        # 可以安全重试。
        #
        # 如果反过来先改 SQLite，
        # Qdrant 更新失败后，下次就无法再通过
        # old_path -> new_path 检测 MOVED。
        # ----------------------------------------------------

        update_document_vector_local_path(
            document_id=(
                document_id
            ),

            local_path=(
                new_path
            ),
        )

        update_document_local_path(
            document_id=(
                document_id
            ),

            local_path=(
                new_path
            ),
        )

        moved_database_paths.add(
            old_path
        )

        moved_disk_paths.add(
            new_path
        )

        result.moved += 1

        print()

        print(
            "[MOVED] "
            f"{database_document['filename']}"
        )

        print(
            "        "
            f"{old_path}"
        )

        print(
            "     -> "
            f"{new_path}"
        )

    # ========================================================
    # 7. 真正 DELETED
    # ========================================================

    deleted_paths = (
        unmatched_database_paths
        - moved_database_paths
    )

    for local_path in sorted(
        deleted_paths
    ):

        document = (
            database_documents[
                local_path
            ]
        )

        print()

        print(
            "[DELETED] "
            f"{document['filename']}"
        )

        remove_document(
            document
        )

        result.deleted += 1

    # ========================================================
    # 8. 真正 NEW
    # ========================================================

    new_paths = (
        unmatched_disk_paths
        - moved_disk_paths
    )

    for local_path in sorted(
        new_paths
    ):

        disk_document = (
            disk_documents[
                local_path
            ]
        )

        print()

        print(
            "[NEW] "
            f"{disk_document['filename']}"
        )

        ingest_pdf(
            pdf_path=(
                disk_document[
                    "path"
                ]
            ),

            content_hash=(
                disk_document[
                    "content_hash"
                ]
            ),
        )

        result.new += 1

    # ========================================================
    # 9. Re-ingest MODIFIED
    # ========================================================

    for local_path in (
        modified_paths
    ):

        disk_document = (
            disk_documents[
                local_path
            ]
        )

        ingest_pdf(
            pdf_path=(
                disk_document[
                    "path"
                ]
            ),

            content_hash=(
                disk_document[
                    "content_hash"
                ]
            ),
        )

    return result