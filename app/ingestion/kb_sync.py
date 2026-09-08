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
    unchanged: int = 0
    hash_backfilled: int = 0


def scan_papers_folder(
    folder: Path,
) -> dict[str, dict]:
    """
    扫描磁盘当前所有 PDF。

    key:
        resolve 后的绝对 local_path

    value:
        path / filename / content_hash
    """

    folder = folder.resolve()

    folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    result = {}

    pdf_files = sorted(
        path
        for path
        in folder.iterdir()
        if (
            path.is_file()
            and path.suffix.lower()
            == ".pdf"
        )
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
    将 data/papers 视为知识库 source of truth。

    自动识别：

    NEW
    MODIFIED
    DELETED
    UNCHANGED
    """

    result = SyncResult()

    # ========================================================
    # 1. 当前磁盘状态
    # ========================================================

    disk_documents = (
        scan_papers_folder(
            papers_folder
        )
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
    # 3. Deleted
    # ========================================================

    deleted_paths = (
        database_paths
        - disk_paths
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
    # 4. Existing:
    #
    # UNCHANGED / MODIFIED / legacy hash backfill
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
        # 旧数据库第一次升级：
        #
        # content_hash=NULL
        #
        # 当前无法知道 PDF 在历史上是否变过，
        # 因此以当前磁盘文件为 baseline，
        # 只补 hash，不做整库重建。
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
        # Unchanged
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
        # Modified
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
    # 5. New
    # ========================================================

    new_paths = (
        disk_paths
        - database_paths
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
                disk_document["path"]
            ),

            content_hash=(
                disk_document[
                    "content_hash"
                ]
            ),
        )

        result.new += 1

    # ========================================================
    # 6. Re-ingest modified
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
                disk_document["path"]
            ),

            content_hash=(
                disk_document[
                    "content_hash"
                ]
            ),
        )

    return result