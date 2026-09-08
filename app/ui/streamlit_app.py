import os

from typing import Any

import httpx
import streamlit as st


# ============================================================
# Configuration
# ============================================================

API_BASE_URL = os.getenv(
    "LITERATURE_AGENT_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

HEALTH_URL = (
    f"{API_BASE_URL}/health"
)

AGENT_RUN_URL = (
    f"{API_BASE_URL}/api/v1/agent/run"
)


# ============================================================
# Page
# ============================================================

st.set_page_config(
    page_title="LiteratureAgent",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# HTTP
# ============================================================

def check_backend() -> dict[str, Any] | None:
    """
    检查 FastAPI 后端状态。
    """

    try:

        response = httpx.get(
            HEALTH_URL,
            timeout=5.0,
        )

        response.raise_for_status()

        return response.json()

    except httpx.HTTPError:

        return None


def ask_agent(
    question: str,
) -> dict[str, Any]:
    """
    通过 HTTP 调用 LiteratureAgent。
    """

    with httpx.Client(
        timeout=httpx.Timeout(
            180.0,
            connect=5.0,
        )
    ) as client:

        response = client.post(
            AGENT_RUN_URL,

            json={
                "question":
                    question,
            },
        )

        response.raise_for_status()

        return response.json()


# ============================================================
# Sidebar
# ============================================================

def render_sidebar(
    health: dict[str, Any] | None,
) -> None:
    """
    Sidebar 放系统状态和示例问题。

    不占用主要科研结果区域。
    """

    with st.sidebar:

        st.header(
            "LiteratureAgent"
        )

        st.caption(
            "Scientific Literature "
            "Intelligence"
        )

        st.divider()

        st.subheader(
            "系统状态"
        )

        if health:

            st.success(
                "Backend Online"
            )

            st.caption(
                f"{health.get('service')} "
                f"· v{health.get('version')}"
            )

        else:

            st.error(
                "Backend Offline"
            )

            st.code(
                "uvicorn "
                "app.api.server:app "
                "--reload"
            )

        st.divider()

        st.subheader(
            "示例问题"
        )

        st.markdown(
            """
**文献问答**

为什么加入 BaTiO3 后压电输出会增强？

**元数据分析**

按页数从多到少排列所有论文

**跨论文定量分析**

比较所有论文作者自己报告的功率密度，
按从高到低排序，并绘制图表

**科学指标抽取**

总结所有论文中出现过的 d33，
包括引用文献中的数据
"""
        )


# ============================================================
# Common
# ============================================================

def render_warning_list(
    warnings: list[str],
) -> None:

    if not warnings:

        st.info(
            "未发现结构化数据质量警告。"
        )

        return

    for warning in warnings:

        st.warning(
            warning
        )


def render_evidence_rows(
    evidence_rows: list[
        dict[str, Any]
    ],
) -> None:
    """
    Evidence 使用折叠卡片，
    避免主页面过长。
    """

    if not evidence_rows:

        st.info(
            "当前结果没有独立 Evidence 记录。"
        )

        return

    for index, row in enumerate(
        evidence_rows,
        start=1,
    ):

        title = (
            row.get(
                "论文"
            )
            or f"Evidence {index}"
        )

        page = row.get(
            "页码"
        )

        label = (
            f"Evidence {index}"
            f" · {title}"
        )

        if page:

            label += (
                f" · Page {page}"
            )

        with st.expander(
            label,
            expanded=False,
        ):

            for (
                field,
                value,
            ) in row.items():

                if value in {
                    None,
                    "",
                }:

                    continue

                st.markdown(
                    f"**{field}**"
                )

                st.write(
                    value
                )


# ============================================================
# Structured Result
# ============================================================

def render_structured_result(
    result: dict[str, Any],
) -> None:
    """
    Structured Result：

    Summary 固定显示。

    Table / Plot / Evidence / Plan
    使用 Tabs。
    """

    final_answer = (
        result.get(
            "final_answer"
        )
        or {}
    )

    # ========================================================
    # Summary
    # ========================================================

    st.subheader(
        "回答摘要"
    )

    summary = (
        final_answer.get(
            "summary"
        )
        or "本次分析未生成摘要。"
    )

    with st.container(
        border=True
    ):

        st.markdown(
            summary
        )

    # ========================================================
    # Tabs
    # ========================================================

    (
        result_tab,
        plot_tab,
        evidence_tab,
        detail_tab,
    ) = st.tabs(
        [
            "分析结果",
            "图表",
            "证据",
            "执行详情",
        ]
    )

    # ========================================================
    # Result Table
    # ========================================================

    with result_tab:

        table_rows = (
            final_answer.get(
                "table_rows"
            )
            or []
        )

        if table_rows:

            st.dataframe(
                table_rows,
                use_container_width=True,
                hide_index=True,
                height=min(
                    520,
                    70
                    + len(table_rows)
                    * 36,
                ),
            )

            st.caption(
                f"共 {len(table_rows)} "
                "条结构化结果"
            )

        else:

            st.info(
                "当前查询没有结构化表格结果。"
            )

        warnings = (
            final_answer.get(
                "warnings"
            )
            or []
        )

        if warnings:

            st.divider()

            st.markdown(
                "#### 数据质量"
            )

            render_warning_list(
                warnings
            )

    # ========================================================
    # Plot
    # ========================================================

    with plot_tab:

        plot_url = result.get(
            "plot_url"
        )

        if plot_url:

            st.image(
                plot_url,
                use_container_width=True,
            )

            st.caption(
                "图表由 LiteratureAgent "
                "确定性分析工具生成。"
            )

        else:

            st.info(
                "本次分析没有生成图表。"
            )

    # ========================================================
    # Evidence
    # ========================================================

    with evidence_tab:

        evidence_rows = (
            final_answer.get(
                "evidence_rows"
            )
            or []
        )

        render_evidence_rows(
            evidence_rows
        )

    # ========================================================
    # Execution Detail
    # ========================================================

    with detail_tab:

        st.markdown(
            "#### Agent Plan"
        )

        plan = result.get(
            "plan"
        )

        if plan:

            st.json(
                plan,
                expanded=False,
            )

        else:

            st.info(
                "没有可展示的执行计划。"
            )

        st.markdown(
            "#### Result Protocol"
        )

        st.code(
            result.get(
                "result_type",
                "unknown",
            )
        )

        plot_path = (
            final_answer.get(
                "plot_path"
            )
        )

        if plot_path:

            st.markdown(
                "#### Server Plot Path"
            )

            st.code(
                plot_path
            )


# ============================================================
# Grounded RAG Result
# ============================================================

def render_grounded_result(
    result: dict[str, Any],
) -> None:
    """
    Grounded RAG Result。
    """

    text_result = (
        result.get(
            "text_result"
        )
        or {}
    )

    text = (
        text_result.get(
            "text"
        )
        or ""
    )

    st.subheader(
        "回答"
    )

    with st.container(
        border=True
    ):

        st.markdown(
            text
        )

    (
        sources_tab,
        detail_tab,
    ) = st.tabs(
        [
            "文献来源",
            "执行详情",
        ]
    )

    # ========================================================
    # Sources
    # ========================================================

    with sources_tab:

        sources = (
            text_result.get(
                "sources"
            )
            or []
        )

        if not sources:

            st.info(
                "本次回答没有返回文献来源。"
            )

        else:

            source_rows = []

            for source in sources:

                score = source.get(
                    "score"
                )

                if isinstance(
                    score,
                    (int, float),
                ):

                    score = round(
                        score,
                        4,
                    )

                source_rows.append(
                    {
                        "来源 ID":
                            source.get(
                                "source_id"
                            ),

                        "论文":
                            source.get(
                                "title"
                            ),

                        "页码":
                            source.get(
                                "page_number"
                            ),

                        "Chunk":
                            source.get(
                                "chunk_index"
                            ),

                        "检索得分":
                            score,
                    }
                )

            st.dataframe(
                source_rows,
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                f"最终回答引用 "
                f"{len(source_rows)} "
                "条文献来源"
            )

    # ========================================================
    # Detail
    # ========================================================

    with detail_tab:

        st.markdown(
            "#### Agent Plan"
        )

        plan = result.get(
            "plan"
        )

        if plan:

            st.json(
                plan,
                expanded=False,
            )

        metadata = (
            text_result.get(
                "metadata"
            )
            or {}
        )

        if metadata:

            st.markdown(
                "#### Retrieval Metadata"
            )

            st.json(
                metadata,
                expanded=False,
            )


# ============================================================
# Result Dispatcher
# ============================================================

def render_agent_result(
    result: dict[str, Any],
) -> None:
    """
    只根据 Result Protocol 分流。
    """

    result_type = result.get(
        "result_type"
    )

    if result_type == "structured":

        render_structured_result(
            result
        )

    elif result_type == "grounded_text":

        render_grounded_result(
            result
        )

    else:

        st.error(
            "收到未知的 Agent "
            "Result Protocol。"
        )


# ============================================================
# Header
# ============================================================

st.title(
    "📚 LiteratureAgent"
)

st.caption(
    "Scientific Literature Retrieval · "
    "Extraction · Analysis · Visualization"
)

st.markdown(
    "面向科研论文的检索、事实抽取、"
    "跨文献定量分析与证据追踪。"
)


# ============================================================
# Health
# ============================================================

health = check_backend()

render_sidebar(
    health
)


# ============================================================
# Question
# ============================================================

with st.container(
    border=True
):

    with st.form(
        "literature_agent_form"
    ):

        question = st.text_area(
            "科研问题",
            placeholder=(
                "例如：比较所有论文作者自己报告的"
                "功率密度，按从高到低排序，并绘制图表"
            ),
            height=110,
        )

        submitted = (
            st.form_submit_button(
                "开始分析",
                type="primary",
                use_container_width=True,
            )
        )


# ============================================================
# Run
# ============================================================

if submitted:

    cleaned_question = (
        question.strip()
    )

    if not cleaned_question:

        st.warning(
            "请输入科研问题。"
        )

    elif health is None:

        st.error(
            "FastAPI 后端当前不可用。"
        )

    else:

        try:

            with st.spinner(
                "LiteratureAgent 正在规划、"
                "检索并分析文献..."
            ):

                result = ask_agent(
                    cleaned_question
                )

            st.session_state[
                "last_agent_result"
            ] = result

            st.session_state[
                "last_question"
            ] = cleaned_question

        except httpx.TimeoutException:

            st.error(
                "Agent 请求超时。"
            )

        except httpx.HTTPStatusError as error:

            response = (
                error.response
            )

            try:

                detail = (
                    response
                    .json()
                    .get(
                        "detail",
                        str(error),
                    )
                )

            except ValueError:

                detail = str(
                    error
                )

            st.error(
                "Agent API 执行失败："
                f"{detail}"
            )

        except httpx.HTTPError as error:

            st.error(
                "无法连接 Agent API："
                f"{error}"
            )


# ============================================================
# Persistent Result
# ============================================================

last_result = (
    st.session_state.get(
        "last_agent_result"
    )
)

if last_result:

    st.divider()

    last_question = (
        st.session_state.get(
            "last_question"
        )
    )

    if last_question:

        st.caption(
            "当前问题"
        )

        st.markdown(
            f"**{last_question}**"
        )

    render_agent_result(
        last_result
    )