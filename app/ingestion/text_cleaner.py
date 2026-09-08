import re


def clean_pdf_text(text: str) -> str:
    """
    清理 PDF 文本提取过程中常见的排版噪声。
    """

    if not text:
        return ""

    # 1. 去掉 soft hyphen
    # 例如 self-\xadpowered -> self-powered
    text = text.replace("\u00ad", "")

    # 2. 不换行空格 -> 普通空格
    text = text.replace("\u00a0", " ")

    # 3. 修复跨行断词
    # 例如：
    # inte-
    # grating
    # ->
    # integrating
    text = re.sub(
        r"(?<=\w)-\s*\n\s*(?=[a-z])",
        "",
        text,
    )

    # 4. 清理每行首尾空格
    lines = [
        line.strip()
        for line in text.splitlines()
    ]

    text = "\n".join(lines)

    # 5. 连续多个空格压缩成一个
    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    # 6. 三个以上连续换行压缩为两个
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()