from pathlib import Path

from qdrant_client import (
    QdrantClient,
)

from qdrant_client.models import (
    Distance,
    PointIdsList,
    VectorParams,
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

QDRANT_PATH = (
    PROJECT_ROOT
    / "data"
    / "qdrant"
)

COLLECTION_NAME = (
    "literature_chunks"
)

VECTOR_SIZE = 1024


def get_qdrant_client() -> QdrantClient:
    """
    创建本地 Qdrant 客户端。
    """

    QDRANT_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )

    return QdrantClient(
        path=str(
            QDRANT_PATH
        )
    )


def init_collection() -> None:
    """
    初始化 Qdrant Collection。
    """

    client = (
        get_qdrant_client()
    )

    try:

        if not client.collection_exists(
            COLLECTION_NAME
        ):

            client.create_collection(
                collection_name=(
                    COLLECTION_NAME
                ),

                vectors_config=(
                    VectorParams(
                        size=VECTOR_SIZE,
                        distance=(
                            Distance.COSINE
                        ),
                    )
                ),
            )

            print(
                "创建 Qdrant Collection："
                f"{COLLECTION_NAME}"
            )

        else:

            print(
                "Qdrant Collection 已存在："
                f"{COLLECTION_NAME}"
            )

    finally:

        client.close()


def get_all_point_ids(
    client: QdrantClient,
    batch_size: int = 256,
) -> set[int | str]:
    """
    分页读取 Collection 中全部 Point ID。

    不读取 vector，
    不读取 payload。

    用于和 SQLite chunks.id
    做 reconciliation。
    """

    if batch_size <= 0:

        raise ValueError(
            "batch_size 必须大于 0。"
        )

    point_ids: set[
        int | str
    ] = set()

    offset = None

    while True:

        (
            records,
            next_offset,
        ) = client.scroll(
            collection_name=(
                COLLECTION_NAME
            ),

            limit=batch_size,

            offset=offset,

            with_payload=False,

            with_vectors=False,
        )

        for record in records:

            point_ids.add(
                record.id
            )

        if next_offset is None:

            break

        offset = next_offset

    return point_ids


def delete_points_by_ids(
    client: QdrantClient,
    point_ids: set[int | str],
    batch_size: int = 256,
) -> int:
    """
    按 Point ID 批量删除 Qdrant 中的 Points。

    返回实际请求删除的 Point 数量。
    """

    if batch_size <= 0:

        raise ValueError(
            "batch_size 必须大于 0。"
        )

    if not point_ids:

        return 0

    ordered_ids = sorted(
        point_ids,
        key=str,
    )

    total = len(
        ordered_ids
    )

    for start in range(
        0,
        total,
        batch_size,
    ):

        batch = ordered_ids[
            start:
            start + batch_size
        ]

        client.delete(
            collection_name=(
                COLLECTION_NAME
            ),

            points_selector=(
                PointIdsList(
                    points=batch
                )
            ),

            wait=True,
        )

    return total