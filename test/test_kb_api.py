from unittest.mock import (
    patch,
)

from fastapi.testclient import (
    TestClient,
)

from app.api.server import app
from app.ingestion.kb_manager import (
    KnowledgeBaseStatus,
    KnowledgeBaseSyncInProgressError,
    KnowledgeBaseUpdateResult,
)


client = TestClient(app)


def make_status(
) -> KnowledgeBaseStatus:

    return KnowledgeBaseStatus(
        source_pdf_count=8,
        indexed_document_count=8,
        page_count=97,
        chunk_count=378,
        vector_count=378,
        pages_without_chunks=0,
        pending_new=0,
        pending_modified=0,
        pending_deleted=0,
        pending_hash_backfill=0,
        sync_required=False,
    )


def test_kb_status_api():

    with patch(
        "app.api.routes."
        "get_knowledge_base_status",

        return_value=make_status(),
    ):

        response = client.get(
            "/api/v1/kb/status"
        )

    assert (
        response.status_code
        == 200
    )

    payload = (
        response.json()
    )

    assert (
        payload[
            "source_pdf_count"
        ]
        == 8
    )

    assert (
        payload[
            "chunk_count"
        ]
        == 378
    )

    assert (
        payload[
            "vector_count"
        ]
        == 378
    )

    assert (
        payload[
            "sync_required"
        ]
        is False
    )


def test_kb_sync_api():

    result = (
        KnowledgeBaseUpdateResult(
            new_documents=1,
            modified_documents=0,
            deleted_documents=0,
            unchanged_documents=8,
            hash_backfilled=0,

            new_chunks=12,

            vector_sqlite_count=390,
            vector_qdrant_count_before=378,
            vectors_added=12,
            stale_vectors_deleted=0,
            vectors_unchanged=378,

            status=(
                KnowledgeBaseStatus(
                    source_pdf_count=9,
                    indexed_document_count=9,
                    page_count=100,
                    chunk_count=390,
                    vector_count=390,
                    pages_without_chunks=0,

                    pending_new=0,
                    pending_modified=0,
                    pending_deleted=0,
                    pending_hash_backfill=0,

                    sync_required=False,
                )
            ),
        )
    )

    with patch(
        "app.api.routes."
        "update_knowledge_base",

        return_value=result,
    ):

        response = client.post(
            "/api/v1/kb/sync"
        )

    assert (
        response.status_code
        == 200
    )

    payload = (
        response.json()
    )

    assert (
        payload[
            "new_documents"
        ]
        == 1
    )

    assert (
        payload[
            "new_chunks"
        ]
        == 12
    )

    assert (
        payload[
            "vectors_added"
        ]
        == 12
    )

    assert (
        payload[
            "status"
        ][
            "source_pdf_count"
        ]
        == 9
    )


def test_kb_sync_conflict():

    with patch(
        "app.api.routes."
        "update_knowledge_base",

        side_effect=(
            KnowledgeBaseSyncInProgressError(
                "知识库同步正在执行，"
                "请稍后再试。"
            )
        ),
    ):

        response = client.post(
            "/api/v1/kb/sync"
        )

    assert (
        response.status_code
        == 409
    )