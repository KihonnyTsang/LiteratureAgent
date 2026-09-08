from app.tools.schemas import (
    TextResult,
)


def render_text_result_markdown(
    result: TextResult,
) -> str:
    """
    确定性渲染 TextResult。

    不再次调用 LLM。

    这样可以保证：

    - [S1] / [S2] 不被改写
    - source title 不被改写
    - page number 不被改写
    - local_path 不被改写
    """

    sections = [
        result.text
    ]

    if result.sources:

        source_lines = []

        for source in result.sources:

            line = (
                f"- [{source.source_id}] "
                f"{source.title}"
            )

            if (
                source.page_number
                is not None
            ):

                line += (
                    f"（第 "
                    f"{source.page_number} "
                    f"页）"
                )

            source_lines.append(
                line
            )

            if source.local_path:

                source_lines.append(
                    f"  - 本地文件："
                    f"{source.local_path}"
                )

        sections.append(
            "## 文献来源\n\n"
            + "\n".join(
                source_lines
            )
        )

    return "\n\n".join(
        sections
    )