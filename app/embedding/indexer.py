import re

from dataclasses import (
    dataclass,
)

from qdrant_client.models import (
    PointStruct,
)

from app.database.sqlite_db import (
    get_all_chunks,
)

from app.embedding.embedding_model import (
    embed_texts,
)

from app.vectorstore.vector_store import (
    COLLECTION_NAME,
    delete_points_by_ids,
    get_all_point_ids,
    get_qdrant_client,
    init_collection,
)


@dataclass
class VectorIndexSyncResult:
    """
    一次向量索引 reconciliation 的结果。
    """

    sqlite_count: int
    qdrant_count_before: int

    added_count: int
    deleted_count: int
    unchanged_count: int


def classify_chunk(
    text: str,
) -> str:
    """
    简单判断 Chunk 是否主要属于参考文献区域。
    """

    # 明确出现 References 标题
    if re.search(
        r"\bREFERENCES\b",
        text,
        flags=re.IGNORECASE,
    ):

        return "reference"

    # 统计类似：
    #
    # 32. J. Tang ...
    # 33. W. Wang ...
    #
    # 的参考文献条目

    reference_entries = (
        re.findall(
            r"(?:^|\n)"
            r"\s*\d{1,3}\."
            r"\s+[A-Z]",
            text,
        )
    )

    # 一个 Chunk 中出现多个连续参考文献条目，
    # 基本可以认定是 bibliography

    if (
        len(reference_entries)
        >= 2
    ):

        return "reference"

    return "content"


def build_point(
    chunk: dict,
    vector,
) -> PointStruct:
    """
    根据 SQLite Chunk 和 Embedding
    构造一个 Qdrant Point。
    """

    return PointStruct(
        # SQLite chunks.id
        # 直接作为 Qdrant Point ID。
        id=chunk["chunk_id"],

        vector=vector.tolist(),

        payload={
            "chunk_id":
                chunk["chunk_id"],

            "document_id":
                chunk["document_id"],

            "page_number":
                chunk["page_number"],

            "chunk_index":
                chunk["chunk_index"],

            "text":
                chunk["text"],

            "title":
                chunk["title"],

            "filename":
                chunk["filename"],

            "local_path":
                chunk["local_path"],

            "chunk_type":
                classify_chunk(
                    chunk["text"]
                ),
        },
    )


def build_vector_index(
    batch_size: int = 16,
) -> VectorIndexSyncResult:
    """
    增量同步 SQLite Chunks 与 Qdrant。

    SQLite chunks.id
        =
    Qdrant Point ID

    因此可以通过集合差确定：

    SQLite - Qdrant
        -> missing points
        -> 需要 Embedding + Upsert

    Qdrant - SQLite
        -> stale points
        -> 需要删除

    SQLite ∩ Qdrant
        -> unchanged
        -> 不重新计算 Embedding
    """

    if batch_size <= 0:

        raise ValueError(
            "batch_size 必须大于 0。"
        )

    # ========================================================
    # 1. SQLite 当前状态
    # ========================================================

    print(
        "读取 SQLite 中的 Chunks..."
    )

    chunks = get_all_chunks()

    print(
        f"共读取 "
        f"{len(chunks)} "
        f"个 Chunks"
    )

    chunks_by_id = {
        chunk["chunk_id"]:
            chunk
        for chunk
        in chunks
    }

    sqlite_ids = set(
        chunks_by_id
    )

    # ========================================================
    # 2. Qdrant 当前状态
    #
    # 注意：
    # 即使 SQLite 现在没有任何 chunk，
    # 也不能提前 return。
    #
    # 因为 Qdrant 可能仍然有 stale points，
    # 需要被删除。
    # ========================================================

    init_collection()

    client = (
        get_qdrant_client()
    )

    try:

        qdrant_ids = (
            get_all_point_ids(
                client
            )
        )

        # ====================================================
        # 3. Reconciliation
        # ====================================================

        missing_ids = (
            sqlite_ids
            - qdrant_ids
        )

        stale_ids = (
            qdrant_ids
            - sqlite_ids
        )

        unchanged_ids = (
            sqlite_ids
            & qdrant_ids
        )

        print()
        print(
            "=" * 60
        )

        print(
            "向量索引状态"
        )

        print(
            "=" * 60
        )

        print(
            "SQLite Chunks："
            f"{len(sqlite_ids)}"
        )

        print(
            "Qdrant Points："
            f"{len(qdrant_ids)}"
        )

        print(
            "待新增向量："
            f"{len(missing_ids)}"
        )

        print(
            "待删除向量："
            f"{len(stale_ids)}"
        )

        print(
            "无需变化："
            f"{len(unchanged_ids)}"
        )

        # ====================================================
        # 4. 删除 stale points
        # ====================================================

        if stale_ids:

            print()
            print(
                "删除 Qdrant 中"
                "已经失效的 Points..."
            )

            delete_points_by_ids(
                client=client,
                point_ids=stale_ids,
            )

            print(
                "已删除 "
                f"{len(stale_ids)} "
                "个失效向量。"
            )

        # ====================================================
        # 5. 没有 missing points
        #
        # 最重要：
        # 这里直接结束。
        #
        # embed_texts() 完全不会被调用，
        # BGE-M3 也不会加载。
        # ====================================================

        if not missing_ids:

            print()
            print(
                "=" * 60
            )

            print(
                "向量索引已同步，"
                "无需重新计算 Embedding。"
            )

            print(
                "=" * 60
            )

            return (
                VectorIndexSyncResult(
                    sqlite_count=(
                        len(sqlite_ids)
                    ),

                    qdrant_count_before=(
                        len(qdrant_ids)
                    ),

                    added_count=0,

                    deleted_count=(
                        len(stale_ids)
                    ),

                    unchanged_count=(
                        len(unchanged_ids)
                    ),
                )
            )

        # ====================================================
        # 6. 只选择缺失的 Chunks
        # ====================================================

        missing_chunks = [
            chunks_by_id[
                chunk_id
            ]
            for chunk_id
            in sorted(
                missing_ids
            )
        ]

        total = len(
            missing_chunks
        )

        print()
        print(
            "开始增量构建向量..."
        )

        # ====================================================
        # 7. 只 Embedding missing chunks
        # ====================================================

        for start in range(
            0,
            total,
            batch_size,
        ):

            batch = (
                missing_chunks[
                    start:
                    start + batch_size
                ]
            )

            texts = [
                item["text"]
                for item
                in batch
            ]

            print()
            print(
                "正在向量化："
                f"{start + 1} ~ "
                f"{min(start + batch_size, total)}"
                f" / {total}"
            )

            vectors = (
                embed_texts(
                    texts
                )
            )

            points = [
                build_point(
                    chunk=chunk,
                    vector=vector,
                )
                for (
                    chunk,
                    vector,
                )
                in zip(
                    batch,
                    vectors,
                )
            ]

            client.upsert(
                collection_name=(
                    COLLECTION_NAME
                ),

                points=points,

                wait=True,
            )

        # ====================================================
        # 8. Result
        # ====================================================

        print()
        print(
            "=" * 60
        )

        print(
            "增量向量索引完成。"
        )

        print(
            "本次新增："
            f"{len(missing_ids)} "
            "个向量"
        )

        print(
            "本次删除："
            f"{len(stale_ids)} "
            "个向量"
        )

        print(
            "=" * 60
        )

        return (
            VectorIndexSyncResult(
                sqlite_count=(
                    len(sqlite_ids)
                ),

                qdrant_count_before=(
                    len(qdrant_ids)
                ),

                added_count=(
                    len(missing_ids)
                ),

                deleted_count=(
                    len(stale_ids)
                ),

                unchanged_count=(
                    len(unchanged_ids)
                ),
            )
        )

    finally:

        client.close()