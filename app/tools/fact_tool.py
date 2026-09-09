from app.database.sqlite_db import (
    get_all_documents,
)

from app.database.fact_repository import (
    ensure_facts_schema,
    has_cached_extraction,
    load_cached_facts,
    replace_facts_for_document_metric,
)

from app.extraction.fact_extractor import (
    extract_facts,
)

from app.extraction.metric_registry import (
    METRIC_REGISTRY,
)

from app.extraction.metric_resolver import (
    resolve_metric_spec,
)

from app.extraction.unit_normalizer import (
    normalize_fact,
)

from app.tools.schemas import (
    ColumnSpec,
    ToolResult,
)


# ============================================================
# 当前 Fact Extraction 版本
#
# 与之前已经生成的 power_density Cache 保持一致。
# ============================================================

EXTRACTION_VERSION = "v2"


# ============================================================
# query_facts 的统一输出字段
# ============================================================

FACT_COLUMNS = [
    "document_id",
    "title",

    # 标准化后的数值
    "value",
    "value_min",
    "value_max",
    "unit",

    # 原始论文数值
    "raw_value",
    "raw_value_min",
    "raw_value_max",
    "raw_unit",

    "value_type",

    "page_number",
    "source_chunk_id",

    "condition_text",
    "evidence",
    "evidence_verified",

    "provenance",
    "confidence",

    "normalization_error",
]

def build_fact_column_specs(
    metric_spec,
) -> list[ColumnSpec]:
    """
    根据 MetricSpec 动态生成科研 Fact 的列语义。

    这里不关心指标是不是：

    - 功率密度
    - d33
    - 电压
    - 击穿场强

    metric_spec 会动态提供指标名称和标准单位。
    """

    metric_name = (
        metric_spec.display_name
    )

    canonical_unit = (
        metric_spec.canonical_unit
    )

    return [

        ColumnSpec(
            field="document_id",
            label="文档 ID",
            role="identifier",
            visible=False,
            format_hint="text",
        ),

        ColumnSpec(
            field="title",
            label="论文",
            role="dimension",
            visible=True,
            format_hint="text",
        ),

        # ====================================================
        # 标准化科学数值
        # ====================================================

        ColumnSpec(
            field="value",
            label=metric_name,
            role="measure",
            visible=True,
            format_hint="number",
            unit=canonical_unit,
            unit_field="unit",
        ),

        ColumnSpec(
            field="value_min",
            label=f"{metric_name}下限",
            role="measure",
            visible=False,
            format_hint="number",
            unit=canonical_unit,
            unit_field="unit",
        ),

        ColumnSpec(
            field="value_max",
            label=f"{metric_name}上限",
            role="measure",
            visible=False,
            format_hint="number",
            unit=canonical_unit,
            unit_field="unit",
        ),

        ColumnSpec(
            field="unit",
            label="标准单位",
            role="unit",
            visible=True,
            format_hint="text",
        ),

        # ====================================================
        # 原始论文数值
        # ====================================================

        ColumnSpec(
            field="raw_value",
            label=f"原始{metric_name}",
            role="raw_measure",
            visible=True,
            format_hint="number",
            unit_field="raw_unit",
        ),

        ColumnSpec(
            field="raw_value_min",
            label=f"原始{metric_name}下限",
            role="raw_measure",
            visible=False,
            format_hint="number",
            unit_field="raw_unit",
        ),

        ColumnSpec(
            field="raw_value_max",
            label=f"原始{metric_name}上限",
            role="raw_measure",
            visible=False,
            format_hint="number",
            unit_field="raw_unit",
        ),

        ColumnSpec(
            field="raw_unit",
            label="原始单位",
            role="unit",
            visible=True,
            format_hint="text",
        ),

        ColumnSpec(
            field="value_type",
            label="数值类型",
            role="metadata",
            visible=False,
            format_hint="text",
        ),

        # ====================================================
        # Provenance
        # ====================================================

        ColumnSpec(
            field="page_number",
            label="页码",
            role="reference",
            visible=True,
            format_hint="integer",
        ),

        ColumnSpec(
            field="source_chunk_id",
            label="Source Chunk",
            role="reference",
            visible=False,
            format_hint="integer",
        ),

        ColumnSpec(
            field="condition_text",
            label="实验条件",
            role="condition",
            visible=True,
            format_hint="text",
        ),

        ColumnSpec(
            field="evidence",
            label="原文证据",
            role="evidence",
            visible=False,
            format_hint="text",
        ),

        ColumnSpec(
            field="evidence_verified",
            label="证据校验",
            role="quality_flag",
            visible=False,
            format_hint="boolean",
        ),

        ColumnSpec(
            field="provenance",
            label="数据来源",
            role="provenance",
            visible=True,
            format_hint="text",
        ),

        ColumnSpec(
            field="confidence",
            label="置信度",
            role="confidence",
            visible=False,
            format_hint="number",
        ),

        ColumnSpec(
            field="normalization_error",
            label="单位归一化错误",
            role="quality_issue",
            visible=False,
            format_hint="text",
        ),
    ]

def resolve_tool_metric(
    metric: str,
):
    """
    将 Planner 给出的自然语言 metric
    转换为 MetricSpec。

    优先复用 Metric Registry，
    避免“功率密度”再次动态生成一个新指标。

    如果 Registry 中没有，
    再调用动态 Metric Resolver。
    """

    metric_text = metric.strip()

    if not metric_text:

        raise ValueError(
            "query_facts 的 metric 不能为空。"
        )

    normalized_text = (
        metric_text.lower()
    )

    # ========================================================
    # 1. 精确匹配 Registry
    # ========================================================

    for (
        key,
        spec,
    ) in METRIC_REGISTRY.items():

        if normalized_text in {
            key.lower(),
            spec.display_name.lower(),
        }:

            return spec

    # ========================================================
    # 2. 唯一的包含关系匹配
    #
    # 例如：
    #
    # 用户：
    # 功率密度
    #
    # Registry：
    # 输出功率密度
    # ========================================================

    partial_matches = []

    for spec in (
        METRIC_REGISTRY.values()
    ):

        display_name = (
            spec.display_name.lower()
        )

        if (
            normalized_text
            in display_name
            or display_name
            in normalized_text
        ):

            partial_matches.append(
                spec
            )

    if len(partial_matches) == 1:

        return partial_matches[0]

    # ========================================================
    # 3. Registry 没有：
    #
    # 例如 d33
    #
    # 让 DeepSeek 动态生成 MetricSpec
    # ========================================================

    return resolve_metric_spec(
        metric_name=None,
        metric_text=metric_text,
    )


def select_documents(
    scope: str,
    document_names: list[str] | None = None,
) -> list[dict]:
    """
    根据 Tool 参数确定处理哪些论文。
    """

    documents = get_all_documents()

    if scope == "all_documents":

        return documents

    if scope != "specific_documents":

        raise ValueError(
            f"未知文档范围：{scope}"
        )

    if not document_names:

        raise ValueError(
            "specific_documents "
            "必须提供 document_names。"
        )

    selected = []

    for requested_name in document_names:

        requested_tokens = [
            token.lower()
            for token
            in requested_name.split()
            if token
        ]

        for document in documents:

            title = (
                document["title"]
                .lower()
            )

            if all(
                token in title
                for token
                in requested_tokens
            ):

                if (
                    document
                    not in selected
                ):

                    selected.append(
                        document
                    )

    return selected


def fact_to_row(
    document: dict,
    fact,
    metric_spec,
) -> dict:
    """
    将 ExtractedFact 转换成统一 ToolResult row。

    重要约定：

    value / unit
    =
    可用于数学运算的标准化数据

    raw_value / raw_unit
    =
    论文原始报告数据
    """

    normalized = normalize_fact(
        fact,
        metric_spec,
    )

    if normalized.converted:

        value = normalized.value
        value_min = (
            normalized.value_min
        )
        value_max = (
            normalized.value_max
        )
        unit = normalized.unit

    else:

        # 单位无法可靠归一化时，
        # 不允许把原始数值伪装成
        # 可以直接比较的数据。
        value = None
        value_min = None
        value_max = None
        unit = None

    return {
        "document_id":
            document["id"],

        "title":
            document["title"],

        # --------------------------------------------
        # 标准化数据
        # --------------------------------------------

        "value":
            value,

        "value_min":
            value_min,

        "value_max":
            value_max,

        "unit":
            unit,

        # --------------------------------------------
        # 原始论文数据
        # --------------------------------------------

        "raw_value":
            fact.value,

        "raw_value_min":
            fact.value_min,

        "raw_value_max":
            fact.value_max,

        "raw_unit":
            fact.unit,

        "value_type":
            fact.value_type,

        # --------------------------------------------
        # Evidence / provenance
        # --------------------------------------------

        "page_number":
            fact.page_number,

        "source_chunk_id":
            fact.chunk_id,

        "condition_text":
            fact.condition_text,

        "evidence":
            fact.evidence,

        "evidence_verified":
            fact.evidence_verified,

        "provenance":
            fact.provenance,

        "confidence":
            fact.confidence,

        "normalization_error":
            normalized.error,
    }


def query_facts(
    metric: str,
    scope: str = "all_documents",
    provenance_scope: str = "author_results",
    document_names: list[str] | None = None,
) -> ToolResult:
    """
    查询已经持久化的跨论文结构化事实。

    重要：

    query_facts 是在线查询工具，
    不负责执行新的 LLM Fact Extraction。

    工作流程：

    1. 解析 Metric
    2. 确定论文范围
    3. 检查 Facts Cache
    4. 只读取已经完成的 extraction cache
    5. Cache Miss 只记录 coverage gap
    6. 单位归一化
    7. 返回 ToolResult + coverage metadata

    新的 Fact Extraction 必须由离线
    fact lifecycle 显式执行。
    """

    metric_spec = resolve_tool_metric(
        metric
    )

    documents = select_documents(
        scope=scope,
        document_names=document_names,
    )

    ensure_facts_schema()

    rows = []

    cache_hit_count = 0
    missing_document_count = 0

    # ========================================================
    # 遍历目标论文
    # ========================================================

    for document in documents:

        document_id = (
            document["id"]
        )

        cache_exists = (
            has_cached_extraction(
                document_id=document_id,

                metric_name=(
                    metric_spec.key
                ),

                extraction_scope=(
                    provenance_scope
                ),

                extraction_version=(
                    EXTRACTION_VERSION
                ),
            )
        )

        # ----------------------------------------------------
        # Cache Miss
        #
        # 在线 query 绝不执行新的 extraction。
        # ----------------------------------------------------

        if not cache_exists:

            print(
                f"Fact Missing："
                f"{document['title']}"
            )

            missing_document_count += 1

            continue

        # ----------------------------------------------------
        # Cache Hit
        # ----------------------------------------------------

        print(
            f"Fact Cache："
            f"{document['title']}"
        )

        facts = (
            load_cached_facts(
                document_id=document_id,

                metric_name=(
                    metric_spec.key
                ),

                extraction_scope=(
                    provenance_scope
                ),

                extraction_version=(
                    EXTRACTION_VERSION
                ),
            )
        )

        cache_hit_count += 1

        # ----------------------------------------------------
        # ExtractedFact -> ToolResult rows
        # ----------------------------------------------------

        for fact in facts:

            rows.append(
                fact_to_row(
                    document=document,
                    fact=fact,
                    metric_spec=metric_spec,
                )
            )

    # ========================================================
    # Coverage
    # ========================================================

    document_count = len(
        documents
    )

    coverage_complete = (
        missing_document_count
        == 0
    )

    if document_count:

        coverage_ratio = (
            cache_hit_count
            / document_count
        )

    else:

        coverage_ratio = 1.0

    # ========================================================
    # Result
    # ========================================================

    return ToolResult(
        columns=FACT_COLUMNS,

        rows=rows,

        column_specs=(
            build_fact_column_specs(
                metric_spec
            )
        ),

        metadata={
            "source":
                "facts",

            "metric_key":
                metric_spec.key,

            "metric_display_name":
                metric_spec.display_name,

            "canonical_unit":
                metric_spec.canonical_unit,

            "provenance_scope":
                provenance_scope,

            # --------------------------------------------
            # Backward-compatible fields
            # --------------------------------------------

            "cache_hit_count":
                cache_hit_count,

            # query_facts 永远不再做 extraction。
            "extraction_count":
                0,

            "document_count":
                document_count,

            "fact_count":
                len(rows),

            # --------------------------------------------
            # Coverage contract
            # --------------------------------------------

            "cached_document_count":
                cache_hit_count,

            "missing_document_count":
                missing_document_count,

            "coverage_complete":
                coverage_complete,

            "coverage_ratio":
                coverage_ratio,

            # --------------------------------------------
            # 数学字段 contract
            # --------------------------------------------

            "numeric_field":
                "value",

            "unit_field":
                "unit",
        },
    )

def update_fact_cache(
    metric: str,
    scope: str = "all_documents",
    provenance_scope: str = "author_results",
    document_names: list[str] | None = None,
    limit: int | None = None,
) -> dict:
    """
    离线、增量更新 Structured Fact Cache。

    与 query_facts 不同：

    这个函数允许执行真正的 LLM Fact Extraction。

    已经存在成功 extraction cache 的文档会跳过。

    limit:
        最多抽取多少篇当前 cache miss 的文档。

        用于：
        - 小批量运行
        - 控制 LLM 成本
        - 中断后增量恢复

    已经成功写入的 extraction 会保留；
    后续重新运行时会自动跳过。
    """

    if (
        limit is not None
        and limit <= 0
    ):

        raise ValueError(
            "limit 必须大于 0。"
        )

    metric_spec = resolve_tool_metric(
        metric
    )

    documents = select_documents(
        scope=scope,
        document_names=document_names,
    )

    ensure_facts_schema()

    cached_document_count = 0
    extracted_document_count = 0
    deferred_document_count = 0
    fact_count = 0

    document_count = len(
        documents
    )

    for index, document in enumerate(
        documents,
        start=1,
    ):

        document_id = (
            document["id"]
        )

        cache_exists = (
            has_cached_extraction(
                document_id=document_id,

                metric_name=(
                    metric_spec.key
                ),

                extraction_scope=(
                    provenance_scope
                ),

                extraction_version=(
                    EXTRACTION_VERSION
                ),
            )
        )

        # ----------------------------------------------------
        # Existing Cache
        # ----------------------------------------------------

        if cache_exists:

            print(
                f"[{index}/{document_count}] "
                "Fact Cache："
                f"{document['title']}"
            )

            facts = (
                load_cached_facts(
                    document_id=document_id,

                    metric_name=(
                        metric_spec.key
                    ),

                    extraction_scope=(
                        provenance_scope
                    ),

                    extraction_version=(
                        EXTRACTION_VERSION
                    ),
                )
            )

            cached_document_count += 1
            fact_count += len(
                facts
            )

            continue

        # ----------------------------------------------------
        # Batch limit
        # ----------------------------------------------------

        if (
            limit is not None
            and extracted_document_count
            >= limit
        ):

            deferred_document_count += 1

            continue

        # ----------------------------------------------------
        # New Extraction
        # ----------------------------------------------------

        print(
            f"[{index}/{document_count}] "
            "Fact Extraction："
            f"{document['title']}"
        )

        facts = extract_facts(
            document_id=document_id,

            metric=metric_spec,

            provenance_scope=(
                provenance_scope
            ),
        )

        replace_facts_for_document_metric(
            document_id=document_id,

            metric_spec=metric_spec,

            facts=facts,

            provenance_scope=(
                provenance_scope
            ),

            extraction_version=(
                EXTRACTION_VERSION
            ),
        )

        extracted_document_count += 1
        fact_count += len(
            facts
        )

    completed_document_count = (
        cached_document_count
        + extracted_document_count
    )

    coverage_complete = (
        completed_document_count
        == document_count
    )

    if document_count:

        coverage_ratio = (
            completed_document_count
            / document_count
        )

    else:

        coverage_ratio = 1.0

    return {
        "metric_key":
            metric_spec.key,

        "metric_display_name":
            metric_spec.display_name,

        "provenance_scope":
            provenance_scope,

        "extraction_version":
            EXTRACTION_VERSION,

        "document_count":
            document_count,

        "cached_document_count":
            cached_document_count,

        "extracted_document_count":
            extracted_document_count,

        "deferred_document_count":
            deferred_document_count,

        "completed_document_count":
            completed_document_count,

        "fact_count":
            fact_count,

        "coverage_complete":
            coverage_complete,

        "coverage_ratio":
            coverage_ratio,
    }