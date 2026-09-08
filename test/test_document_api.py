from unittest.mock import (
    patch,
)

from fastapi.testclient import (
    TestClient,
)

from app.api.server import app


client = TestClient(app)


def make_document(
    *,
    document_id: str = "doc-001",
    filename: str = "paper.pdf",
    local_path: str | None = None,
) -> dict:
    """
    构造测试用 Document 记录。

    保持原有 regression fixture 不变，
    只允许测试按需覆盖 local_path。
    """

    if local_path is None:

        local_path = (
            "/private/server/path/"
            f"{filename}"
        )

    return {
        "id":
            document_id,

        "title":
            "Example Scientific Paper",

        "filename":
            filename,

        "local_path":
            local_path,

        "page_count":
            12,
    }


def test_document_catalog():

    with patch(
        "app.api.routes."
        "get_all_documents",

        return_value=[
            make_document()
        ],
    ):

        response = client.get(
            "/api/v1/documents"
        )

    assert (
        response.status_code
        == 200
    )

    payload = response.json()

    assert len(payload) == 1

    document = payload[0]

    assert (
        document[
            "document_id"
        ]
        == "doc-001"
    )

    assert (
        document[
            "title"
        ]
        == "Example Scientific Paper"
    )

    assert (
        document[
            "filename"
        ]
        == "paper.pdf"
    )

    assert (
        document[
            "page_count"
        ]
        == 12
    )

    # HTTP API 不允许暴露
    # 服务器内部 local_path。
    assert (
        "local_path"
        not in document
    )


def test_document_pdf_api(
    tmp_path,
):

    papers_folder = (
        tmp_path
        / "papers"
    )

    papers_folder.mkdir()

    pdf_path = (
        papers_folder
        / "paper.pdf"
    )

    pdf_path.write_bytes(
        b"%PDF-1.4\n"
        b"test document\n"
        b"%%EOF\n"
    )

    with (
        patch(
            "app.api.routes."
            "PAPERS_FOLDER",

            papers_folder,
        ),

        patch(
            "app.api.routes."
            "get_document_by_id",

            return_value=(
                    make_document(
                        local_path=str(
                            pdf_path
                        )
                    )
            ),
        ),
    ):

        response = client.get(
            "/api/v1/documents/"
            "doc-001/pdf"
        )

    assert (
        response.status_code
        == 200
    )

    assert (
        response.headers[
            "content-type"
        ]
        .startswith(
            "application/pdf"
        )
    )

    assert response.content.startswith(
        b"%PDF-1.4"
    )


def test_document_pdf_not_found():

    with patch(
        "app.api.routes."
        "get_document_by_id",

        return_value=None,
    ):

        response = client.get(
            "/api/v1/documents/"
            "missing-document/pdf"
        )

    assert (
        response.status_code
        == 404
    )


def test_document_pdf_rejects_path_escape(
    tmp_path,
):

    papers_folder = (
        tmp_path
        / "papers"
    )

    papers_folder.mkdir()

    secret_pdf = (
        tmp_path
        / "secret.pdf"
    )

    secret_pdf.write_bytes(
        b"%PDF-1.4\n"
        b"secret\n"
        b"%%EOF\n"
    )

    malicious_document = (
        make_document(
            filename="secret.pdf",

            local_path=str(
                secret_pdf
            ),
        )
    )

    with (
        patch(
            "app.api.routes."
            "PAPERS_FOLDER",

            papers_folder,
        ),

        patch(
            "app.api.routes."
            "get_document_by_id",

            return_value=(
                malicious_document
            ),
        ),
    ):

        response = client.get(
            "/api/v1/documents/"
            "doc-001/pdf"
        )

    assert (
        response.status_code
        == 404
    )