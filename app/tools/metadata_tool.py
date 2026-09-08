from app.database.sqlite_db import (
    get_all_documents,
)

from app.tools.schemas import (
    ColumnSpec,
    ToolResult,
)


# ============================================================
# 允许 Agent 读取的 Metadata 字段
#
# 这是 Tool Contract，
# 不是针对用户问题硬编码。
# ============================================================

AVAILABLE_METADATA_FIELDS = {
    "id",
    "title",
    "filename",
    "local_path",
    "page_count",
}

METADATA_COLUMN_SPECS = {

    "id": ColumnSpec(
        field="id",
        label="文档 ID",
        role="identifier",
        visible=False,
        format_hint="text",
    ),

    "title": ColumnSpec(
        field="title",
        label="论文",
        role="dimension",
        visible=True,
        format_hint="text",
    ),

    "filename": ColumnSpec(
        field="filename",
        label="文件名",
        role="dimension",
        visible=True,
        format_hint="text",
    ),

    "local_path": ColumnSpec(
        field="local_path",
        label="本地文件",
        role="reference",
        visible=False,
        format_hint="path",
    ),

    "page_count": ColumnSpec(
        field="page_count",
        label="页数",
        role="measure",
        visible=True,
        format_hint="integer",
        unit="页",
    ),
}

def query_metadata(
    fields: list[str],
    scope: str = "all_documents",
) -> ToolResult:
    """
    查询 documents 表中的文档元数据。

    当前第一版只实现 all_documents。
    """

    if not fields:

        raise ValueError(
            "query_metadata 至少需要一个字段。"
        )

    # --------------------------------------------------------
    # 字段安全验证
    # --------------------------------------------------------

    invalid_fields = [
        field
        for field in fields
        if field
        not in AVAILABLE_METADATA_FIELDS
    ]

    if invalid_fields:

        raise ValueError(
            "query_metadata 不支持字段："
            + ", ".join(
                invalid_fields
            )
        )

    if scope != "all_documents":

        raise ValueError(
            "当前 query_metadata "
            "暂时只支持 all_documents。"
        )

    documents = get_all_documents()

    rows = []

    for document in documents:

        row = {}

        for field in fields:

            row[field] = (
                document[field]
            )

        rows.append(
            row
        )

    column_specs = [
        METADATA_COLUMN_SPECS[
            field
        ].model_copy(
            deep=True
        )
        for field in fields
    ]

    return ToolResult(
        columns=fields,

        rows=rows,

        column_specs=column_specs,

        metadata={
            "source":
                "documents",

            "row_count":
                len(rows),
        },
    )