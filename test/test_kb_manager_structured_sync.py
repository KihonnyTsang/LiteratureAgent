from types import SimpleNamespace
from unittest.mock import patch

from app.ingestion.kb_manager import (
    update_knowledge_base,
)


def test_kb_sync_runs_structured_enrichment_after_vector_sync(
) -> None:

    sync_result = SimpleNamespace(
        new=1,
        modified=0,
        deleted=0,
        moved=0,
        unchanged=8,
        hash_backfilled=0,
    )

    vector_result = SimpleNamespace(
        sqlite_count=390,
        qdrant_count_before=378,
        added_count=12,
        deleted_count=0,
        unchanged_count=378,
    )

    status = object()

    with (
        patch(
            "app.ingestion.kb_manager."
            "init_db"
        ) as init_db,

        patch(
            "app.ingestion.kb_manager."
            "sync_knowledge_base",
            return_value=sync_result,
        ) as sync_kb,

        patch(
            "app.ingestion.kb_manager."
            "build_chunks_for_all_pages",
            return_value=12,
        ) as build_chunks,

        patch(
            "app.ingestion.kb_manager."
            "build_vector_index",
            return_value=vector_result,
        ) as build_vectors,

        patch(
            "app.ingestion.kb_manager."
            "update_structured_knowledge",
            return_value={
                "structured": "ok",
            },
        ) as structured_update,

        patch(
            "app.ingestion.kb_manager."
            "get_knowledge_base_status",
            return_value=status,
        ) as get_status,
    ):

        result = update_knowledge_base()

    init_db.assert_called_once_with()
    sync_kb.assert_called_once()
    build_chunks.assert_called_once_with()
    build_vectors.assert_called_once_with()
    structured_update.assert_called_once_with()
    get_status.assert_called_once_with()

    assert result.new_documents == 1
    assert result.new_chunks == 12
    assert result.vectors_added == 12
    assert result.status is status
