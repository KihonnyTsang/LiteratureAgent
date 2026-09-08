from app.embedding.embedding_model import (
    embed_query,
)

from app.vectorstore.vector_store import (
    get_qdrant_client,
    COLLECTION_NAME,
)

from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue,
)


def semantic_search(
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """
    使用 BGE-M3 + Qdrant
    进行语义检索。
    """

    # 用户问题 -> 向量
    query_vector = embed_query(query)

    client = get_qdrant_client()

    result = client.query_points(
        collection_name=COLLECTION_NAME,

        query=query_vector.tolist(),

        query_filter=Filter(
            must_not=[
                FieldCondition(
                    key="chunk_type",
                    match=MatchValue(
                        value="reference"
                    ),
                )
            ]
        ),

        limit=top_k,

        with_payload=True,
    )

    client.close()

    results = []

    for point in result.points:

        results.append(
            {
                "score":
                    point.score,

                "chunk_id":
                    point.payload.get(
                        "chunk_id"
                    ),

                "document_id":
                    point.payload.get(
                        "document_id"
                    ),

                "page_number":
                    point.payload.get(
                        "page_number"
                    ),

                "chunk_index":
                    point.payload.get(
                        "chunk_index"
                    ),

                "text":
                    point.payload.get(
                        "text"
                    ),

                "title":
                    point.payload.get(
                        "title"
                    ),

                "filename":
                    point.payload.get(
                        "filename"
                    ),

                "local_path":
                    point.payload.get(
                        "local_path"
                    ),
            }
        )

    return results

def semantic_search_in_document(
    query: str,
    document_id: str,
    top_k: int = 6,
) -> list[dict]:
    """
    只在指定文献中进行语义检索。
    """

    query_vector = embed_query(query)

    client = get_qdrant_client()

    result = client.query_points(
        collection_name=COLLECTION_NAME,

        query=query_vector.tolist(),

        query_filter=Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(
                        value=document_id
                    ),
                )
            ],

            must_not=[
                FieldCondition(
                    key="chunk_type",
                    match=MatchValue(
                        value="reference"
                    ),
                )
            ],
        ),

        limit=top_k,

        with_payload=True,
    )

    client.close()

    results = []

    for point in result.points:

        results.append(
            {
                "score": point.score,

                "chunk_id":
                    point.payload.get("chunk_id"),

                "document_id":
                    point.payload.get("document_id"),

                "page_number":
                    point.payload.get("page_number"),

                "chunk_index":
                    point.payload.get("chunk_index"),

                "text":
                    point.payload.get("text"),

                "title":
                    point.payload.get("title"),

                "filename":
                    point.payload.get("filename"),

                "local_path":
                    point.payload.get("local_path"),
            }
        )

    return results