from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
)


ColumnRole = Literal[
    "identifier",
    "dimension",
    "measure",
    "unit",
    "raw_measure",
    "condition",
    "reference",
    "evidence",
    "provenance",
    "confidence",
    "quality_flag",
    "quality_issue",
    "metadata",
]


FormatHint = Literal[
    "text",
    "number",
    "integer",
    "boolean",
    "path",
]


class ColumnSpec(BaseModel):
    """
    描述 ToolResult 中某一列的语义。

    field:
        Python / Table 使用的真实字段名。

    label:
        面向用户的语义名称。

    role:
        这一列在数据分析中的角色。

    visible:
        默认展示时是否建议显示。

    format_hint:
        给未来 Renderer / UI 的显示提示。

    unit:
        如果该 measure 有固定标准单位，
        可以直接记录在这里。

    unit_field:
        如果单位来自另一列，
        记录对应的 unit field。
    """

    field: str

    label: str

    role: ColumnRole

    visible: bool = True

    format_hint: FormatHint | None = None

    unit: str | None = None

    unit_field: str | None = None


class ToolResult(BaseModel):
    """
    Agent Tool 的统一结构化输出。

    columns:
        实际字段顺序。

    rows:
        实际数据。

    column_specs:
        columns 的语义描述。

    metadata:
        整张表的上下文信息。
    """

    columns: list[str]

    rows: list[
        dict[str, Any]
    ] = Field(
        default_factory=list
    )

    column_specs: list[
        ColumnSpec
    ] = Field(
        default_factory=list
    )

    metadata: dict[
        str,
        Any,
    ] = Field(
        default_factory=dict
    )

    def get_column_spec(
        self,
        field: str,
    ) -> ColumnSpec | None:
        """
        根据字段名获取对应 ColumnSpec。
        """

        for spec in self.column_specs:

            if spec.field == field:
                return spec

        return None

class SourceRef(BaseModel):
    """
    文本型 ToolResult 的来源引用。

    当前 RAG 使用这些字段，
    后续也可以复用于其他带来源的文本工具。
    """

    source_id: str

    title: str

    page_number: int | None = None

    chunk_index: int | None = None

    filename: str | None = None

    local_path: str | None = None

    score: float | None = None


class TextResult(BaseModel):
    """
    已经生成完成的 grounded 文本结果。

    与 ToolResult 的区别：

    ToolResult:
        用于结构化数据分析。

    TextResult:
        用于已经完成 grounded generation
        的文本型工具，例如 RAG QA。
    """

    text: str

    sources: list[
        SourceRef
    ] = Field(
        default_factory=list
    )

    metadata: dict[
        str,
        Any,
    ] = Field(
        default_factory=dict
    )