from pathlib import Path
from unittest.mock import patch

from app.ingestion.kb_sync import (
    sync_knowledge_base,
)

from app.ingestion.kb_manager import (
    get_knowledge_base_status,
)

def test_same_hash_new_path_is_moved(
    tmp_path,
):

    library = (
        tmp_path
        / "Zotero"
    )

    old_path = str(
        (
            tmp_path
            / "old-library"
            / "paper.pdf"
        ).resolve()
    )

    new_path = str(
        (
            library
            / "storage"
            / "ABC123"
            / "paper.pdf"
        ).resolve()
    )

    database_document = {
        "id":
            "doc_test",

        "title":
            "Test Paper",

        "filename":
            "paper.pdf",

        "local_path":
            old_path,

        "content_hash":
            "same-content-hash",
    }

    disk_documents = {
        new_path: {
            "path":
                Path(new_path),

            "filename":
                "paper.pdf",

            "content_hash":
                "same-content-hash",
        }
    }

    with (
        patch(
            "app.ingestion.kb_sync."
            "scan_papers_folder",

            return_value=(
                disk_documents
            ),
        ),

        patch(
            "app.ingestion.kb_sync."
            "get_documents_for_sync",

            return_value=[
                database_document
            ],
        ),

        patch(
            "app.ingestion.kb_sync."
            "update_document_vector_local_path"
        ) as update_vector_path,

        patch(
            "app.ingestion.kb_sync."
            "update_document_local_path"
        ) as update_path,

        patch(
            "app.ingestion.kb_sync."
            "remove_document"
        ) as remove_document,

        patch(
            "app.ingestion.kb_sync."
            "ingest_pdf"
        ) as ingest_pdf,
    ):

        result = (
            sync_knowledge_base(
                library
            )
        )

    assert result.moved == 1
    assert result.new == 0
    assert result.deleted == 0
    assert result.modified == 0

    update_vector_path.assert_called_once_with(
        document_id="doc_test",
        local_path=new_path,
    )

    update_path.assert_called_once_with(
        document_id="doc_test",
        local_path=new_path,
    )

    remove_document.assert_not_called()

    ingest_pdf.assert_not_called()


def test_different_hash_is_new_and_deleted(
    tmp_path,
):

    library = (
        tmp_path
        / "library"
    )

    old_path = str(
        (
            tmp_path
            / "old"
            / "paper.pdf"
        ).resolve()
    )

    new_path = str(
        (
            library
            / "new-paper.pdf"
        ).resolve()
    )

    database_document = {
        "id":
            "doc_test",

        "title":
            "Test Paper",

        "filename":
            "paper.pdf",

        "local_path":
            old_path,

        "content_hash":
            "old-hash",
    }

    disk_documents = {
        new_path: {
            "path":
                Path(new_path),

            "filename":
                "new-paper.pdf",

            "content_hash":
                "new-hash",
        }
    }

    with (
        patch(
            "app.ingestion.kb_sync."
            "scan_papers_folder",

            return_value=(
                disk_documents
            ),
        ),

        patch(
            "app.ingestion.kb_sync."
            "get_documents_for_sync",

            return_value=[
                database_document
            ],
        ),

        patch(
            "app.ingestion.kb_sync."
            "update_document_local_path"
        ) as update_path,

        patch(
            "app.ingestion.kb_sync."
            "remove_document"
        ) as remove_document,

        patch(
            "app.ingestion.kb_sync."
            "ingest_pdf"
        ) as ingest_pdf,
    ):

        result = (
            sync_knowledge_base(
                library
            )
        )

    assert result.moved == 0
    assert result.new == 1
    assert result.deleted == 1

    update_path.assert_not_called()

    remove_document.assert_called_once()

    ingest_pdf.assert_called_once()

def test_exact_duplicate_new_pdfs_are_ingested_once(
    tmp_path,
):

    library = (
        tmp_path
        / "library"
    )

    first_path = str(
        (
            library
            / "docs"
            / "paper.pdf"
        ).resolve()
    )

    second_path = str(
        (
            library
            / "storage"
            / "ABC123"
            / "paper-copy.pdf"
        ).resolve()
    )

    same_hash = (
        "same-content-hash"
    )

    disk_documents = {
        first_path: {
            "path":
                Path(first_path),

            "filename":
                "paper.pdf",

            "content_hash":
                same_hash,
        },

        second_path: {
            "path":
                Path(second_path),

            "filename":
                "paper-copy.pdf",

            "content_hash":
                same_hash,
        },
    }

    with (
        patch(
            "app.ingestion.kb_sync."
            "scan_papers_folder",

            return_value=(
                disk_documents
            ),
        ),

        patch(
            "app.ingestion.kb_sync."
            "get_documents_for_sync",

            return_value=[],
        ),

        patch(
            "app.ingestion.kb_sync."
            "ingest_pdf"
        ) as ingest_pdf,

        patch(
            "app.ingestion.kb_sync."
            "remove_document"
        ) as remove_document,
    ):

        result = (
            sync_knowledge_base(
                library
            )
        )

    assert result.new == 1
    assert result.deleted == 0
    assert result.moved == 0

    ingest_pdf.assert_called_once()

    remove_document.assert_not_called()

    expected_path = min(
        first_path,
        second_path,
    )

    call_kwargs = (
        ingest_pdf
        .call_args
        .kwargs
    )

    assert (
        str(
            call_kwargs[
                "pdf_path"
            ]
        )
        == expected_path
    )

    assert (
        call_kwargs[
            "content_hash"
        ]
        == same_hash
    )

def test_kb_status_recognizes_moved_document(
    tmp_path,
):

    old_path = str(
        (
            tmp_path
            / "old-library"
            / "existing.pdf"
        ).resolve()
    )

    moved_path = str(
        (
            tmp_path
            / "new-library"
            / "existing.pdf"
        ).resolve()
    )

    new_path = str(
        (
            tmp_path
            / "new-library"
            / "new.pdf"
        ).resolve()
    )

    database_document = {
        "id":
            "doc_existing",

        "title":
            "Existing Paper",

        "filename":
            "existing.pdf",

        "local_path":
            old_path,

        "content_hash":
            "existing-hash",
    }

    raw_disk_documents = {
        moved_path: {
            "path":
                Path(moved_path),

            "filename":
                "existing.pdf",

            "content_hash":
                "existing-hash",
        },

        new_path: {
            "path":
                Path(new_path),

            "filename":
                "new.pdf",

            "content_hash":
                "new-hash",
        },
    }

    with (
        patch(
            "app.ingestion.kb_manager."
            "init_db"
        ),

        patch(
            "app.ingestion.kb_manager."
            "scan_papers_folder",

            return_value=(
                raw_disk_documents
            ),
        ),

        patch(
            "app.ingestion.kb_manager."
            "get_documents_for_sync",

            return_value=[
                database_document
            ],
        ),

        patch(
            "app.ingestion.kb_manager."
            "_get_sqlite_counts",

            return_value=(
                1,
                0,
                0,
                0,
            ),
        ),

        patch(
            "app.ingestion.kb_manager."
            "_get_vector_count",

            return_value=0,
        ),
    ):

        status = (
            get_knowledge_base_status()
        )

    assert (
        status.source_pdf_count
        == 2
    )

    assert (
        status.indexed_document_count
        == 1
    )

    assert (
        status.pending_new
        == 1
    )

    assert (
        status.pending_moved
        == 1
    )

    assert (
        status.pending_modified
        == 0
    )

    assert (
        status.pending_deleted
        == 0
    )

    assert (
        status.pending_hash_backfill
        == 0
    )

    assert (
        status.sync_required
        is True
    )