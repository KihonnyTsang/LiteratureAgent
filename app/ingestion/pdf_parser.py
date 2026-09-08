from pathlib import Path

import pymupdf


def parse_pdf(pdf_path: Path) -> list[dict]:
    """
    读取 PDF，并按页提取文本。

    Parameters
    ----------
    pdf_path : Path
        PDF 文件路径。

    Returns
    -------
    list[dict]
        每一项代表 PDF 的一页，例如：

        {
            "page_number": 1,
            "text": "第一页的文本内容"
        }
    """

    document = pymupdf.open(pdf_path)

    pages = []

    for page_index, page in enumerate(document):
        text = page.get_text("text").strip()

        pages.append(
            {
                "page_number": page_index + 1,
                "text": text,
            }
        )

    document.close()

    return pages