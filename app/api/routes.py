import logging

from dataclasses import (
    asdict,
)
from pathlib import (
    Path,
)

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
)

from fastapi.responses import (
    FileResponse,
)

from app.database.sqlite_db import (
    get_all_documents,
    get_document_by_id,
)
from app.agent.plan_validator import (
    PlanValidationError,
)
from app.agent.runtime import (
    run_agent,
)
from app.agent.runtime_schemas import (
    AgentRunResult,
)
from app.api.schemas import (
    AgentRunAPIResponse,
    AgentRunRequest,
    HealthResponse,
    KnowledgeBaseStatusResponse,
    KnowledgeBaseSyncResponse,
    DocumentReferenceResponse,
)
from app.ingestion.kb_manager import (
    KnowledgeBaseSyncInProgressError,
    get_knowledge_base_status,
    update_knowledge_base,
    PAPERS_FOLDER,
)


logger = logging.getLogger(
    __name__
)

router = APIRouter()

def resolve_document_pdf_path(
    document: dict,
) -> Path:
    """
    将数据库中的 document
    安全映射回 data/papers 中的 PDF。

    注意：

    不直接相信 local_path。

    这是为了：

    1. 不暴露宿主机绝对路径；
    2. Docker 后仍然可移植；
    3. 防止路径穿越。
    """

    papers_root = (
        PAPERS_FOLDER
        .resolve()
    )

    filename = (
        document.get(
            "filename"
        )
    )

    if not filename:

        raise FileNotFoundError(
            "论文文件名不存在。"
        )

    pdf_path = (
        papers_root
        / filename
    ).resolve()

    try:

        pdf_path.relative_to(
            papers_root
        )

    except ValueError as error:

        raise FileNotFoundError(
            "论文路径不合法。"
        ) from error

    if (
        not pdf_path.is_file()
        or pdf_path.suffix.lower()
        != ".pdf"
    ):

        raise FileNotFoundError(
            "论文 PDF 文件不存在。"
        )

    return pdf_path

def build_plot_url(
    result: AgentRunResult,
    request: Request,
) -> str | None:
    """
    将 Runtime 的本地 plot_path
    转换成 HTTP URL。

    这里只使用最终文件名，
    不允许把任意本地路径暴露成静态 URL。
    """

    final_answer = (
        result.final_answer
    )

    if final_answer is None:

        return None

    plot_path = (
        final_answer.plot_path
    )

    if not plot_path:

        return None

    filename = (
        Path(plot_path)
        .name
    )

    return str(
        request.url_for(
            "plots",
            path=filename,
        )
    )


@router.get(
    "/health",

    response_model=HealthResponse,

    tags=[
        "System",
    ],
)
def health_check() -> HealthResponse:
    """
    轻量健康检查。

    不加载 Embedding，
    不调用 LLM，
    不访问知识库。
    """

    return HealthResponse(
        status="ok",
        service="LiteratureAgent",
        version="0.1.0",
    )


@router.get(
    "/api/v1/documents",

    response_model=list[
        DocumentReferenceResponse
    ],

    tags=[
        "Documents",
    ],
)
def list_documents_api(
) -> list[
    DocumentReferenceResponse
]:
    """
    返回当前已经索引的论文目录。

    不暴露服务器 local_path。
    """

    try:

        documents = (
            get_all_documents()
        )

        return [
            DocumentReferenceResponse(
                document_id=(
                    document["id"]
                ),

                title=(
                    document["title"]
                ),

                filename=(
                    document["filename"]
                ),

                page_count=(
                    document.get(
                        "page_count"
                    )
                ),
            )

            for document
            in documents
        ]

    except Exception as error:

        logger.exception(
            "读取论文目录失败。"
        )

        raise HTTPException(
            status_code=500,

            detail=(
                "LiteratureAgent "
                "论文目录读取失败。"
            ),
        ) from error


@router.get(
    "/api/v1/documents/"
    "{document_id}/pdf",

    tags=[
        "Documents",
    ],
)
def document_pdf_api(
    document_id: str,
) -> FileResponse:
    """
    通过 document_id 返回原始 PDF。

    PDF 只允许来自：

        data/papers/

    不允许客户端提交任意文件路径。
    """

    document = (
        get_document_by_id(
            document_id
        )
    )

    if document is None:

        raise HTTPException(
            status_code=404,
            detail="论文不存在。",
        )

    try:

        pdf_path = (
            resolve_document_pdf_path(
                document
            )
        )

    except FileNotFoundError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    return FileResponse(
        path=str(
            pdf_path
        ),

        media_type=(
            "application/pdf"
        ),
    )


@router.get(
    "/api/v1/kb/status",

    response_model=(
        KnowledgeBaseStatusResponse
    ),

    tags=[
        "Knowledge Base",
    ],
)
def knowledge_base_status_api(
) -> KnowledgeBaseStatusResponse:
    """
    读取知识库当前状态。

    不执行同步，
    不调用 LLM，
    不计算新的 Embedding。
    """

    try:

        status = (
            get_knowledge_base_status()
        )

        return (
            KnowledgeBaseStatusResponse(
                **asdict(status)
            )
        )

    except Exception as error:

        logger.exception(
            "读取知识库状态失败。"
        )

        raise HTTPException(
            status_code=500,

            detail=(
                "LiteratureAgent "
                "知识库状态读取失败。"
            ),
        ) from error


@router.post(
    "/api/v1/kb/sync",

    response_model=(
        KnowledgeBaseSyncResponse
    ),

    tags=[
        "Knowledge Base",
    ],
)
def sync_knowledge_base_api(
) -> KnowledgeBaseSyncResponse:
    """
    执行完整知识库同步。

    data/papers
        ↓
    SQLite
        ↓
    Chunks
        ↓
    Qdrant
    """

    try:

        result = (
            update_knowledge_base()
        )

        return (
            KnowledgeBaseSyncResponse
            .model_validate(
                asdict(result)
            )
        )

    except (
        KnowledgeBaseSyncInProgressError
    ) as error:

        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error

    except Exception as error:

        logger.exception(
            "知识库同步失败。"
        )

        raise HTTPException(
            status_code=500,

            detail=(
                "LiteratureAgent "
                "知识库同步失败。"
            ),
        ) from error


@router.post(
    "/api/v1/agent/run",

    response_model=(
        AgentRunAPIResponse
    ),

    tags=[
        "Agent",
    ],
)
def run_agent_api(
    request_body: AgentRunRequest,
    request: Request,
) -> AgentRunAPIResponse:
    """
    执行一次完整 LiteratureAgent 请求。
    """

    try:

        result = run_agent(
            request_body.question
        )

        plot_url = (
            build_plot_url(
                result=result,
                request=request,
            )
        )

        return AgentRunAPIResponse(
            **result.model_dump(),
            plot_url=plot_url,
        )

    except PlanValidationError as error:

        raise HTTPException(
            status_code=422,

            detail=str(
                error
            ),
        ) from error

    except Exception as error:

        logger.exception(
            "Agent API 执行失败。"
        )

        raise HTTPException(
            status_code=500,

            detail=(
                "LiteratureAgent "
                "执行失败。"
            ),
        ) from error