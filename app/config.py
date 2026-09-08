import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

ENV_FILE = (
    PROJECT_ROOT
    / ".env"
)

load_dotenv(
    ENV_FILE,
    override=False,
)

DEFAULT_PAPERS_FOLDER = (
    PROJECT_ROOT
    / "data"
    / "papers"
)


def get_papers_folder() -> Path:
    """
    返回 LiteratureAgent 的 PDF 根目录。

    优先读取：

        LITERATURE_AGENT_PAPERS_DIR

    支持：

        ~/Zotero
        /absolute/path
        relative/path

    未配置时继续使用：

        data/papers
    """

    configured = (
        os.getenv(
            "LITERATURE_AGENT_PAPERS_DIR",
            "",
        )
        .strip()
    )

    if not configured:

        DEFAULT_PAPERS_FOLDER.mkdir(
            parents=True,
            exist_ok=True,
        )

        return (
            DEFAULT_PAPERS_FOLDER
            .resolve()
        )

    expanded = os.path.expandvars(
        configured
    )

    path = (
        Path(expanded)
        .expanduser()
    )

    if not path.is_absolute():

        path = (
            PROJECT_ROOT
            / path
        )

    return path.resolve()