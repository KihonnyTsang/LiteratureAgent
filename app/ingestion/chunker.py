from app.ingestion.text_cleaner import clean_pdf_text

from app.database.sqlite_db import (
    get_all_pages,
    chunks_exist,
    insert_chunks,
)

def split_text_into_chunks(
    text: str,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> list[str]:
    """
    将文本切分成带重叠区域的 Chunk。

    Parameters
    ----------
    text:
        原始文本

    chunk_size:
        每个 Chunk 最大字符数

    overlap:
        相邻 Chunk 重叠字符数

    Returns
    -------
    list[str]
        分块后的文本列表
    """

    text = clean_pdf_text(text)

    if not text:
        return []

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        end = min(
            start + chunk_size,
            text_length,
        )

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        # 已经到文本末尾
        if end >= text_length:
            break

        start = end - overlap

    return chunks

def build_chunks_for_all_pages() -> int:
    """
    为数据库中的所有页面建立 Chunk。

    返回本次实际新增的 Chunk 数量。
    """

    pages = get_all_pages()

    print(
        f"准备处理 "
        f"{len(pages)} "
        "个页面"
    )

    total_chunks = 0

    for page in pages:

        document_id = (
            page["document_id"]
        )

        page_number = (
            page["page_number"]
        )

        text = page["text"]

        # 已经处理过的页面直接跳过
        if chunks_exist(
            document_id=document_id,
            page_number=page_number,
        ):

            continue

        chunks = (
            split_text_into_chunks(
                text
            )
        )

        insert_chunks(
            document_id=document_id,
            page_number=page_number,
            chunks=chunks,
        )

        total_chunks += len(
            chunks
        )

    print(
        f"本次新生成 "
        f"{total_chunks} "
        "个 Chunks"
    )

    return total_chunks