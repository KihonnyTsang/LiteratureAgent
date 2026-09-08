from typing import Literal

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

from app.agent.runtime_schemas import (
    AgentRunResult,
)


class HealthResponse(BaseModel):
    """
    API 健康检查响应。
    """

    status: Literal["ok"]

    service: str

    version: str

class DocumentReferenceResponse(
    BaseModel
):
    """
    浏览器可见的论文资源元数据。

    故意不暴露 local_path。
    """

    document_id: str

    title: str

    filename: str

    page_count: int | None = None

class KnowledgeBaseStatusResponse(
    BaseModel
):
    """
    知识库状态响应。
    """

    source_pdf_count: int

    indexed_document_count: int

    page_count: int

    chunk_count: int

    vector_count: int

    pages_without_chunks: int

    pending_new: int

    pending_modified: int

    pending_deleted: int

    pending_moved: int

    pending_hash_backfill: int

    sync_required: bool


class KnowledgeBaseSyncResponse(
    BaseModel
):
    """
    一次完整知识库同步响应。
    """

    new_documents: int

    modified_documents: int

    deleted_documents: int

    moved_documents: int

    unchanged_documents: int

    hash_backfilled: int

    new_chunks: int

    vector_sqlite_count: int

    vector_qdrant_count_before: int

    vectors_added: int

    stale_vectors_deleted: int

    vectors_unchanged: int

    status: (
        KnowledgeBaseStatusResponse
    )


class AgentRunRequest(BaseModel):
    """
    Agent API 请求。
    """

    question: str = Field(
        min_length=1,
        description=(
            "用户提交的科研文献问题。"
        ),
    )

    @field_validator(
        "question"
    )
    @classmethod
    def validate_question(
        cls,
        value: str,
    ) -> str:
        """
        清理并验证用户问题。
        """

        cleaned = (
            value.strip()
        )

        if not cleaned:

            raise ValueError(
                "question 不能为空。"
            )

        return cleaned


class AgentRunAPIResponse(
    AgentRunResult
):
    """
    FastAPI 对 AgentRunResult
    增加的 HTTP-specific 信息。

    Agent Runtime 本身仍然只负责
    本地 plot_path。

    API Layer 再把它映射为
    浏览器可访问的 plot_url。
    """

    plot_url: str | None = Field(
        default=None,

        description=(
            "如果本次 Agent 生成图表，"
            "这里提供对应的 HTTP URL。"
        ),
    )