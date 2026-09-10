import os

from typing import Any
from urllib.parse import quote

import httpx
import streamlit as st


# ============================================================
# Configuration
# ============================================================

API_BASE_URL = os.getenv(
    "LITERATURE_AGENT_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

PUBLIC_API_BASE_URL = os.getenv(
    "LITERATURE_AGENT_PUBLIC_API_URL",
    API_BASE_URL,
).rstrip("/")

HEALTH_URL = (
    f"{API_BASE_URL}/health"
)

AGENT_RUN_URL = (
    f"{API_BASE_URL}/api/v1/agent/run"
)

KB_STATUS_URL = (
    f"{API_BASE_URL}/api/v1/kb/status"
)

KB_SYNC_URL = (
    f"{API_BASE_URL}/api/v1/kb/sync"
)

DOCUMENTS_URL = (
    f"{API_BASE_URL}/api/v1/documents"
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

def get_kb_status(
) -> dict[str, Any] | None:
    """
    读取知识库状态。

    只调用 FastAPI，
    Streamlit 不直接访问 SQLite / Qdrant。
    """

    try:

        response = httpx.get(
            KB_STATUS_URL,
            timeout=10.0,
        )

        response.raise_for_status()

        return response.json()

    except httpx.HTTPError:

        return None


def request_kb_sync(
) -> dict[str, Any]:
    """
    请求 FastAPI 执行完整知识库同步。

    新增 PDF 时可能需要计算 Embedding，
    因此这里允许较长的读取超时。
    """

    with httpx.Client(
        timeout=httpx.Timeout(
            600.0,
            connect=5.0,
        )
    ) as client:

        response = client.post(
            KB_SYNC_URL
        )

        response.raise_for_status()

        return response.json()


def get_document_catalog(
) -> list[dict[str, Any]]:
    """
    从 FastAPI 获取当前已经索引的论文目录。

    Streamlit 不直接读取 SQLite。
    """

    try:

        response = httpx.get(
            DOCUMENTS_URL,
            timeout=10.0,
        )

        response.raise_for_status()

        payload = response.json()

        if not isinstance(
            payload,
            list,
        ):

            return []

        return payload

    except httpx.HTTPError:

        return []


def build_document_lookup(
    documents: list[
        dict[str, Any]
    ],
) -> dict[str, dict]:
    """
    构建 UI 用论文查找表。

    同时支持：

    title
    filename

    如果 title / filename 出现重复，
    不建立该 key 的映射，
    防止打开错误论文。
    """

    title_buckets = {}
    filename_buckets = {}

    for document in documents:

        title = document.get(
            "title"
        )

        filename = document.get(
            "filename"
        )

        if title:

            title_buckets.setdefault(
                title,
                [],
            ).append(
                document
            )

        if filename:

            filename_buckets.setdefault(
                filename,
                [],
            ).append(
                document
            )

    by_title = {
        key: values[0]
        for key, values
        in title_buckets.items()
        if len(values) == 1
    }

    by_filename = {
        key: values[0]
        for key, values
        in filename_buckets.items()
        if len(values) == 1
    }

    return {
        "by_title":
            by_title,

        "by_filename":
            by_filename,
    }


def find_document_reference(
    document_lookup: dict[
        str,
        dict
    ],

    *,
    title: str | None = None,
    filename: str | None = None,
) -> dict | None:
    """
    根据 filename / title
    找到对应 document reference。

    filename 优先。
    """

    by_filename = (
        document_lookup.get(
            "by_filename",
            {},
        )
    )

    if (
        filename
        and filename in by_filename
    ):

        return (
            by_filename[
                filename
            ]
        )

    by_title = (
        document_lookup.get(
            "by_title",
            {},
        )
    )

    if (
        title
        and title in by_title
    ):

        return (
            by_title[
                title
            ]
        )

    return None


def normalize_page_number(
    value: Any,
) -> int | None:
    """
    将 Renderer / RAG 返回的页码
    安全转换成 PDF page fragment。
    """

    if value is None:

        return None

    try:

        page_number = int(
            float(
                str(value).strip()
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        return None

    if page_number <= 0:

        return None

    return page_number


def build_pdf_url(
    document_id: str,
    page_number: int | None = None,
) -> str:
    """
    构建浏览器可访问 PDF URL。

    注意这里使用 PUBLIC_API_BASE_URL，
    而不是 Streamlit Container 内部 API URL。
    """

    encoded_document_id = quote(
        str(document_id),
        safe="",
    )

    url = (
        f"{PUBLIC_API_BASE_URL}"
        f"/api/v1/documents/"
        f"{encoded_document_id}"
        f"/pdf"
    )

    if page_number:

        url += (
            f"#page="
            f"{page_number}"
        )

    return url


def get_reference_pdf_url(
    document_lookup: dict[
        str,
        dict
    ],

    *,
    title: str | None = None,
    filename: str | None = None,
    page_number: Any = None,
) -> str | None:
    """
    从 UI reference 信息生成 PDF URL。
    """

    document = (
        find_document_reference(
            document_lookup,
            title=title,
            filename=filename,
        )
    )

    if document is None:

        return None

    document_id = document.get(
        "document_id"
    )

    if not document_id:

        return None

    resolved_page = (
        normalize_page_number(
            page_number
        )
    )

    return build_pdf_url(
        document_id=document_id,
        page_number=resolved_page,
    )

def add_pdf_links_to_table_rows(
    table_rows: list[
        dict[str, Any]
    ],

    document_lookup: dict[
        str,
        dict
    ],
) -> list[dict[str, Any]]:
    """
    给结构化结果增加：

        原文

    链接列。

    原始 table_rows 不修改。
    """

    result = []

    for row in table_rows:

        title = row.get(
            "论文"
        )

        page_number = row.get(
            "页码"
        )

        pdf_url = (
            get_reference_pdf_url(
                document_lookup,
                title=title,
                page_number=(
                    page_number
                ),
            )
        )

        display_row = {}

        for field, value in (
            row.items()
        ):

            display_row[
                field
            ] = value

            # 原文列尽量紧跟论文列
            if (
                field == "论文"
                and pdf_url
            ):

                display_row[
                    "原文"
                ] = pdf_url

        # 某些表可能没有“论文”列，
        # 不强行增加链接。
        result.append(
            display_row
        )

    return result


# ============================================================
# Sidebar
# ============================================================

def render_sidebar(
    health: dict[str, Any] | None,
    kb_status: dict[str, Any] | None,
) -> None:
    """
    Sidebar：

    - Backend 状态
    - Knowledge Base 状态
    - Knowledge Base 同步入口
    - 最近一次同步结果
    - 示例问题
    """

    with st.sidebar:

        st.header(
            "LiteratureAgent"
        )

        st.caption(
            "Scientific Literature "
            "Intelligence"
        )

        # ====================================================
        # Backend
        # ====================================================

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

        # ====================================================
        # Knowledge Base
        # ====================================================

        st.divider()

        st.subheader(
            "知识库"
        )

        if kb_status is None:

            if health:

                st.warning(
                    "暂时无法读取知识库状态。"
                )

            else:

                st.caption(
                    "Backend 启动后可读取"
                    "知识库状态。"
                )

        else:

            # ------------------------------------------------
            # Core counts
            # ------------------------------------------------

            column_1, column_2 = (
                st.columns(2)
            )

            with column_1:

                st.metric(
                    "PDF",
                    kb_status.get(
                        "source_pdf_count",
                        0,
                    ),
                )

            with column_2:

                st.metric(
                    "Documents",
                    kb_status.get(
                        "indexed_document_count",
                        0,
                    ),
                )

            column_3, column_4 = (
                st.columns(2)
            )

            with column_3:

                st.metric(
                    "Pages",
                    kb_status.get(
                        "page_count",
                        0,
                    ),
                )

            with column_4:

                st.metric(
                    "Chunks",
                    kb_status.get(
                        "chunk_count",
                        0,
                    ),
                )

            st.metric(
                "Vectors",
                kb_status.get(
                    "vector_count",
                    0,
                ),
            )

            # ------------------------------------------------
            # Sync state
            # ------------------------------------------------

            sync_required = bool(
                kb_status.get(
                    "sync_required",
                    False,
                )
            )

            if sync_required:

                st.warning(
                    "检测到未同步的知识库变化"
                )

                st.caption(
                    "待新增 "
                    f"{kb_status.get('pending_new', 0)}"
                    " · 待修改 "
                    f"{kb_status.get('pending_modified', 0)}"
                    " · 待移动 "
                    f"{kb_status.get('pending_moved', 0)}"
                    " · 待删除 "
                    f"{kb_status.get('pending_deleted', 0)}"
                )

                pages_without_chunks = (
                    kb_status.get(
                        "pages_without_chunks",
                        0,
                    )
                )

                if pages_without_chunks:

                    st.caption(
                        "待生成 Chunk 的页面："
                        f"{pages_without_chunks}"
                    )

            else:

                st.success(
                    "知识库已同步"
                )

        # ====================================================
        # Sync button
        # ====================================================

        sync_clicked = st.button(
            "同步知识库",
            type="secondary",
            use_container_width=True,
            disabled=(
                health is None
            ),
        )

        if sync_clicked:

            try:

                with st.spinner(
                    "正在同步 PDF、Chunks、"
                    "向量索引与结构化事实..."
                ):

                    sync_result = (
                        request_kb_sync()
                    )

                st.session_state[
                    "last_kb_sync_result"
                ] = sync_result

                # 重新运行页面，
                # 从 /kb/status 获取同步后的真实状态。
                st.rerun()

            except httpx.TimeoutException:

                st.error(
                    "知识库同步请求超时。"
                )

            except (
                httpx.HTTPStatusError
            ) as error:

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
                    "知识库同步失败："
                    f"{detail}"
                )

            except httpx.HTTPError as error:

                st.error(
                    "无法连接知识库 API："
                    f"{error}"
                )

        # ====================================================
        # Last sync
        # ====================================================

        last_sync = (
            st.session_state.get(
                "last_kb_sync_result"
            )
        )

        if last_sync:

            st.caption(
                "最近一次同步"
            )

            st.markdown(
                "新增 "
                f"**{last_sync.get('new_documents', 0)}**"
                " · 修改 "
                f"**{last_sync.get('modified_documents', 0)}**"
                " · 移动 "
                f"**{last_sync.get('moved_documents', 0)}**"
                " · 删除 "
                f"**{last_sync.get('deleted_documents', 0)}**"
            )

            st.caption(
                "新增 Chunks "
                f"{last_sync.get('new_chunks', 0)}"
                " · 新增 Vectors "
                f"{last_sync.get('vectors_added', 0)}"
            )

        # ====================================================
        # Examples
        # ====================================================

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

    document_lookup: dict[
        str,
        dict
    ],
) -> None:
    """
    Evidence 使用折叠卡片。

    如果能够解析对应论文，
    提供直接打开 PDF / 指定页面的入口。
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

        page_number = (
            normalize_page_number(
                page
            )
        )

        pdf_url = (
            get_reference_pdf_url(
                document_lookup,
                title=title,
                page_number=(
                    page_number
                ),
            )
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

            # ================================================
            # Original PDF
            # ================================================

            if pdf_url:

                st.link_button(
                    label=title,

                    url=pdf_url,

                    help=(
                        "打开对应论文原文"
                    ),
                )

                if page_number:

                    st.caption(
                        "点击上方论文标题，"
                        f"直接打开原文 Page "
                        f"{page_number}。"
                    )

                else:

                    st.caption(
                        "点击上方论文标题"
                        "打开原文 PDF。"
                    )

                st.divider()

            # ================================================
            # Evidence fields
            # ================================================

            for (
                field,
                value,
            ) in row.items():

                if value in {
                    None,
                    "",
                }:

                    continue

                # 标题已经作为 PDF link
                # 单独展示，不再重复一次。
                if (
                    field == "论文"
                    and pdf_url
                ):

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

    document_lookup: dict[
        str,
        dict
    ],
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

            display_rows = (
                add_pdf_links_to_table_rows(
                    table_rows=table_rows,
                    document_lookup=(
                        document_lookup
                    ),
                )
            )

            has_pdf_links = any(
                row.get(
                    "原文"
                )
                for row
                in display_rows
            )

            column_config = {}

            if has_pdf_links:
                column_config[
                    "原文"
                ] = (
                    st.column_config
                    .LinkColumn(
                        "原文",

                        help=(
                            "打开对应论文 PDF。"
                            "如果结果包含页码，"
                            "会尽量直接跳到该页。"
                        ),

                        display_text=(
                            "打开 PDF ↗"
                        ),
                    )
                )

            st.dataframe(
                display_rows,
                use_container_width=True,
                hide_index=True,

                column_config=(
                    column_config
                ),

                height=min(
                    520,
                    70
                    + len(display_rows)
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
            evidence_rows=(
                evidence_rows
            ),

            document_lookup=(
                document_lookup
            ),
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

    document_lookup: dict[
        str,
        dict
    ],
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

                pdf_url = (
                    get_reference_pdf_url(
                        document_lookup,

                        title=source.get(
                            "title"
                        ),

                        filename=source.get(
                            "filename"
                        ),

                        page_number=source.get(
                            "page_number"
                        ),
                    )
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

                        "原文":
                            pdf_url,
                    }
                )

            st.dataframe(
                source_rows,

                use_container_width=True,

                hide_index=True,

                column_config={
                    "原文":
                        st.column_config
                        .LinkColumn(
                            "原文",

                            help=(
                                "打开对应原文页。"
                            ),

                            display_text=(
                                "打开原文 ↗"
                            ),
                        ),
                },
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

    document_lookup: dict[
        str,
        dict
    ],
) -> None:
    """
    只根据 Result Protocol 分流。
    """

    result_type = result.get(
        "result_type"
    )

    if result_type == "structured":

        render_structured_result(
            result=result,

            document_lookup=(
                document_lookup
            ),
        )

    elif (
        result_type
        == "grounded_text"
    ):

        render_grounded_result(
            result=result,

            document_lookup=(
                document_lookup
            ),
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

kb_status = (
    get_kb_status()
    if health
    else None
)

render_sidebar(
    health=health,
    kb_status=kb_status,
)

document_catalog = (
    get_document_catalog()
    if health
    else []
)

document_lookup = (
    build_document_lookup(
        document_catalog
    )
)


# ============================================================
# Question
# ============================================================

knowledge_base_outdated = bool(
    kb_status
    and kb_status.get(
        "sync_required",
        False,
    )
)

if knowledge_base_outdated:

    st.warning(
        "检测到 data/papers 与当前知识库不同步。"
        "请先在左侧点击「同步知识库」，"
        "再进行文献分析。"
    )

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
                disabled=(
                        health is None
                        or knowledge_base_outdated
                ),
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


    elif knowledge_base_outdated:

        st.warning(

            "知识库存在未同步变化，"

            "请先执行知识库同步。"

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
        result=last_result,

        document_lookup=(
            document_lookup
        ),
    )
