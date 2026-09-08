from pathlib import Path

from fastapi import (
    FastAPI,
)

from fastapi.staticfiles import (
    StaticFiles,
)

from app.api.routes import (
    router,
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

PLOTS_DIR = (
    PROJECT_ROOT
    / "data"
    / "plots"
)


def create_app() -> FastAPI:
    """
    创建 LiteratureAgent FastAPI Application。
    """

    PLOTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    application = FastAPI(
        title="LiteratureAgent API",

        description=(
            "面向科研文献检索、"
            "结构化事实抽取、"
            "跨论文分析与可视化的 "
            "AI Agent API。"
        ),

        version="0.1.0",

        docs_url="/docs",

        redoc_url="/redoc",

        openapi_url=(
            "/openapi.json"
        ),
    )

    # ========================================================
    # Agent API
    # ========================================================

    application.include_router(
        router
    )

    # ========================================================
    # Static Plot Files
    #
    # data/plots/example.png
    #
    # ->
    #
    # /static/plots/example.png
    # ========================================================

    application.mount(
        "/static/plots",

        StaticFiles(
            directory=str(
                PLOTS_DIR
            ),
        ),

        name="plots",
    )

    return application


app = create_app()