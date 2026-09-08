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
)
from app.ingestion.kb_manager import (
    KnowledgeBaseSyncInProgressError,
    get_knowledge_base_status,
    update_knowledge_base,
)


logger = logging.getLogger(
    __name__
)

router = APIRouter()


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