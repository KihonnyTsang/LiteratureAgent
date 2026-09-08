from pathlib import Path

import pytest

from app.ingestion.kb_sync import (
    scan_papers_folder,
)


def write_fake_pdf(
    path: Path,
    content: bytes,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_bytes(
        b"%PDF-1.4\n"
        + content
        + b"\n%%EOF\n"
    )


def test_scan_papers_folder_recursive(
    tmp_path,
):

    root = (
        tmp_path
        / "Zotero"
    )

    first_pdf = (
        root
        / "storage"
        / "ABC123"
        / "paper-one.pdf"
    )

    second_pdf = (
        root
        / "storage"
        / "XYZ456"
        / "nested"
        / "paper-two.PDF"
    )

    ignored_file = (
        root
        / "storage"
        / "ABC123"
        / "notes.txt"
    )

    write_fake_pdf(
        first_pdf,
        b"paper one",
    )

    write_fake_pdf(
        second_pdf,
        b"paper two",
    )

    ignored_file.write_text(
        "not a pdf"
    )

    result = (
        scan_papers_folder(
            root
        )
    )

    assert len(result) == 2

    paths = set(
        result.keys()
    )

    assert (
        str(first_pdf.resolve())
        in paths
    )

    assert (
        str(second_pdf.resolve())
        in paths
    )

    filenames = {
        item["filename"]
        for item
        in result.values()
    }

    assert filenames == {
        "paper-one.pdf",
        "paper-two.PDF",
    }


def test_scan_papers_folder_returns_hashes(
    tmp_path,
):

    root = (
        tmp_path
        / "library"
    )

    pdf_path = (
        root
        / "a"
        / "paper.pdf"
    )

    write_fake_pdf(
        pdf_path,
        b"stable content",
    )

    result = (
        scan_papers_folder(
            root
        )
    )

    record = result[
        str(pdf_path.resolve())
    ]

    assert record[
        "content_hash"
    ]

    assert record[
        "path"
    ] == pdf_path.resolve()


def test_scan_papers_folder_rejects_missing_root(
    tmp_path,
):

    missing = (
        tmp_path
        / "does-not-exist"
    )

    with pytest.raises(
        FileNotFoundError
    ):

        scan_papers_folder(
            missing
        )