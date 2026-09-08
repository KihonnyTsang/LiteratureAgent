import hashlib

from pathlib import Path
from uuid import uuid4

from app.ingestion.pdf_parser import (
    parse_pdf,
)

from app.database.sqlite_db import (
    document_exists,
    insert_document_with_pages,
)


def calculate_file_hash(
    file_path: Path,
) -> str:
    """
    计算文件 SHA-256。

    使用流式读取，
    避免一次性把整个 PDF 读入内存。
    """

    sha256 = hashlib.sha256()

    with file_path.open(
        "rb"
    ) as file:

        while True:

            block = file.read(
                1024 * 1024
            )

            if not block:
                break

            sha256.update(
                block
            )

    return sha256.hexdigest()


def ingest_pdf(
    pdf_path: Path,
    content_hash: str | None = None,
):
    """
    将单篇 PDF 导入文献库。
    """

    pdf_path = pdf_path.resolve()

    print()
    print(
        f"正在处理："
        f"{pdf_path.name}"
    )

    # --------------------------------------------------------
    # 检查是否已经入库
    # --------------------------------------------------------

    if document_exists(
        str(pdf_path)
    ):
        print(
            "已经存在于文献库中，跳过。"
        )
        return

    # --------------------------------------------------------
    # Hash
    # --------------------------------------------------------

    if content_hash is None:

        content_hash = (
            calculate_file_hash(
                pdf_path
            )
        )

    # --------------------------------------------------------
    # Parse
    # --------------------------------------------------------

    pages = parse_pdf(
        pdf_path
    )

    # --------------------------------------------------------
    # Document ID
    # --------------------------------------------------------

    document_id = (
        f"doc_{uuid4().hex[:12]}"
    )

    # v0.1 暂时使用文件名作为论文标题
    title = pdf_path.stem

    # --------------------------------------------------------
    # SQLite
    # --------------------------------------------------------

    insert_document_with_pages(
        document_id=document_id,
        title=title,
        filename=pdf_path.name,
        local_path=str(pdf_path),
        pages=pages,
        content_hash=content_hash,
    )

    print(
        "入库成功"
    )

    print(
        f"Document ID："
        f"{document_id}"
    )

    print(
        f"标题：{title}"
    )

    print(
        f"页数：{len(pages)}"
    )


def ingest_folder(
    folder: Path,
):
    """
    扫描文件夹中的所有 PDF 并入库。

    保留这个函数用于简单导入场景。

    正式 Knowledge Base Update
    将由 kb_sync.py 负责 reconciliation。
    """

    pdf_files = [
        path
        for path
        in folder.iterdir()
        if (
            path.is_file()
            and path.suffix.lower()
            == ".pdf"
        )
    ]

    pdf_files.sort()

    print(
        f"发现 "
        f"{len(pdf_files)} "
        f"篇 PDF"
    )

    for pdf_path in pdf_files:

        try:

            ingest_pdf(
                pdf_path
            )

        except Exception as error:

            print(
                f"处理失败："
                f"{pdf_path.name}"
            )

            print(
                f"错误：{error}"
            )