import json
import re

from app.extraction.schemas import (
    MetricSpec,
    LLMExtractionResult,
    ExtractedFact,
)

from app.extraction.metric_registry import (
    get_metric_spec,
)

from app.rag.retriever import (
    semantic_search_in_document,
)

from app.llm.siliconflow_client import chat


def retrieve_candidates(
    document_id: str,
    metric_spec: MetricSpec,
    per_query: int = 4,
    max_candidates: int = 10,
) -> list[dict]:
    """
    根据一个指标的多个检索表达，
    在指定论文内召回候选 Chunk。
    """

    candidates_by_chunk = {}

    for query in metric_spec.search_queries:

        results = semantic_search_in_document(
            query=query,
            document_id=document_id,
            top_k=per_query,
        )

        for result in results:

            chunk_id = result["chunk_id"]

            # 同一 Chunk 可能被多个 query 搜到，
            # 只保留最高相似度版本。
            old_result = candidates_by_chunk.get(
                chunk_id
            )

            if (
                old_result is None
                or result["score"]
                > old_result["score"]
            ):
                candidates_by_chunk[
                    chunk_id
                ] = result

    candidates = list(
        candidates_by_chunk.values()
    )

    candidates.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return candidates[:max_candidates]


def build_extraction_context(
    candidates: list[dict],
) -> tuple[str, dict]:
    """
    给候选 Chunk 分配 S1、S2……
    同时建立来源映射。
    """

    parts = []

    source_map = {}

    for index, item in enumerate(
        candidates,
        start=1,
    ):

        source_id = f"S{index}"

        source_map[source_id] = item

        parts.append(
            f"""
[{source_id}]
Page: {item["page_number"]}
Chunk: {item["chunk_index"]}

{item["text"]}
""".strip()
        )

    context = "\n\n".join(parts)

    return context, source_map


def parse_json_response(
    response: str,
) -> dict:
    """
    从 LLM 返回内容中解析 JSON。

    即使模型偶尔加 ```json 代码块，
    这里也尽量兼容。
    """

    text = response.strip()

    # 删除 Markdown code fence
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^```\s*",
        "",
        text,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    # 提取最外层 JSON object
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(
            "LLM 返回内容中没有找到 JSON。"
        )

    json_text = text[start:end + 1]

    return json.loads(json_text)


def normalize_for_compare(
    text: str,
) -> str:
    """
    用于检查 evidence 是否真的存在于原文中。
    """

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip().lower()


def extract_facts(
    document_id: str,
    metric: str | MetricSpec,
    provenance_scope: str = "author_results",
) -> list[ExtractedFact]:
    """
    通用科研事实抽取器。

    metric 可以是：
        "power_density"

    也可以直接传入自定义 MetricSpec。
    """

    # ==========================
    # 1. 获取指标定义
    # ==========================

    if isinstance(metric, str):
        metric_spec = get_metric_spec(metric)
    else:
        metric_spec = metric

    # ==========================
    # 2. 检索候选证据
    # ==========================

    candidates = retrieve_candidates(
        document_id=document_id,
        metric_spec=metric_spec,
    )

    if not candidates:
        return []

    context, source_map = (
        build_extraction_context(
            candidates
        )
    )

    # ==========================
    # 3. 构造 Prompt
    # ==========================

    valid_units = ", ".join(
        metric_spec.valid_units
    )

    exclude_terms = ", ".join(
        metric_spec.exclude_terms
    )

    if provenance_scope == "author_results":

        provenance_rule = """
    数据来源规则：

    只提取当前论文作者自己的实验结果、
    计算结果或作者明确报告的本研究器件结果。

    不要把以下内容作为目标事实：
    - Introduction 中引用其他论文的数据
    - Literature comparison 中其他研究者的数据
    - References 中的数据

    所有返回事实的 provenance 必须为：
    author_result
    """.strip()

    elif provenance_scope == "all_mentions":

        provenance_rule = """
    数据来源规则：

    可以提取：
    1. 当前论文作者自己的研究结果；
    2. 论文正文中明确提到的其他文献数据。

    必须使用 provenance 区分数据来源：

    author_result
    = 当前论文作者自己的研究结果

    cited_literature
    = 当前论文引用的其他研究结果

    uncertain
    = 根据当前片段无法可靠判断来源

    不得把不同 provenance 的事实混淆。
    """.strip()

    else:
        raise ValueError(
            f"未知 provenance_scope：{provenance_scope}"
        )

    # ==========================
    # 根据用户要求生成数据来源规则
    # ==========================

    if provenance_scope == "author_results":

        provenance_rule = """
    数据来源规则：

    只提取当前论文作者自己的研究结果，包括：
    - 当前论文作者自己的实验结果
    - 当前论文作者自己的计算结果
    - 当前论文作者明确报告的本研究器件结果

    不要把以下内容作为目标事实：
    - Introduction 中引用其他论文的数据
    - Literature review 中其他研究者的数据
    - Comparison table 中其他论文的数据
    - References 中的数据

    所有返回事实的 provenance 必须为：
    "author_result"
    """.strip()

    elif provenance_scope == "all_mentions":

        provenance_rule = """
    数据来源规则：

    可以提取：
    1. 当前论文作者自己的研究结果；
    2. 当前论文正文中明确提到或引用的其他文献数据。

    必须使用 provenance 字段区分数据来源：

    "author_result"
    = 当前论文作者自己的研究结果

    "cited_literature"
    = 当前论文引用或讨论的其他研究结果

    "uncertain"
    = 根据当前提供的片段无法可靠判断数据来源

    不得把 cited_literature 误标记为 author_result。
    """.strip()

    else:

        raise ValueError(
            f"未知 provenance_scope：{provenance_scope}"
        )

    # ==========================
    # 构造 System Prompt
    # ==========================

    system_prompt = f"""
    你是一名严谨的科研数据抽取系统。

    你的任务是从提供的科研论文原文片段中，
    抽取指定的科研指标，并返回结构化数据。

    ==============================
    目标指标
    ==============================

    名称：
    {metric_spec.display_name}

    内部名称：
    {metric_spec.key}

    定义：
    {metric_spec.description}

    常见合法单位：
    {valid_units}

    容易混淆、需要排除的概念：
    {exclude_terms}

    ==============================
    基本规则
    ==============================

    1. 只能依据当前提供的论文原文片段抽取数据。

    2. 不允许使用外部知识补充论文中没有提供的数据。

    3. 不允许自行计算论文没有明确报告的新数值。

    例如：
    如果论文只给出了 voltage 和 current，
    但没有明确报告 power density，
    不要自行计算 power density。

    4. 必须严格区分目标指标与名称相似但物理含义不同的指标。

    例如：

    power density != energy density

    power density != current density

    power density != illumination power density

    power density != solar simulator power density

    power density != PCE

    5. 一篇论文可能报告多个合法的目标指标。

    例如：
    同一个器件可能在不同测试条件下报告多个 power density。

    这种情况下 facts 中可以返回多条事实。

    6. 如果同一个实验结果在摘要、正文和结论中重复出现，
    只保留一条，不要因为重复出现而生成多个 Fact。

    7. 每一条 Fact 都必须提供 source_id。

    source_id 只能使用当前上下文提供的：

    S1
    S2
    S3
    ...

    禁止自行编造不存在的 source_id。

    8. evidence 必须来自 source_id 对应的原文片段。

    evidence 应尽量保留能够直接支持该数据的原始短句，
    不要把自己的解释写进 evidence。

    9. condition_text 用于记录该数值对应的重要实验条件。

    例如：

    - load resistance
    - pressure
    - frequency
    - strain
    - temperature
    - composition
    - filler loading
    - electric field

    如果原文没有明确条件，可以返回 null。

    10. confidence 必须为 0 到 1 之间的小数。

    ==============================
    数值类型规则
    ==============================

    科研数据不一定是单个数字。

    value_type 只能取以下四种值：

    "scalar"
    表示单个明确数值。

    例如：
    10.1 μW/cm²

    此时：
    value = 10.1
    value_min = null
    value_max = null


    "range"
    表示一个范围。

    例如：
    120–960 pC/N

    此时：
    value = null
    value_min = 120
    value_max = 960


    "lower_bound"
    表示下限。

    例如：
    >180000 cycles

    此时：
    value = 180000
    value_min = null
    value_max = null


    "upper_bound"
    表示上限。

    例如：
    <5 %

    此时：
    value = 5
    value_min = null
    value_max = null


    不要因为数值前有：
    ~
    approximately
    about
    around

    就改变 value_type。

    例如：

    ~8.22 mW/cm²

    仍然应该表示为：

    value_type = "scalar"
    value = 8.22

    ==============================
    数据来源规则
    ==============================

    {provenance_rule}

    ==============================
    无结果规则
    ==============================

    如果当前提供的论文片段中没有可靠的目标指标：

    found 必须为 false。

    此时必须返回：

    facts = []

    不要为了完成任务而猜测或编造数值。

    ==============================
    返回格式
    ==============================

    你必须只返回合法 JSON。

    不要返回 Markdown。

    不要使用 ```json 代码块。

    不要解释。

    不要在 JSON 前后添加任何文字。


    如果找到单个数值，例如 10.1 μW/cm²：

    {{
      "found": true,
      "facts": [
        {{
          "value_type": "scalar",
          "value": 10.1,
          "value_min": null,
          "value_max": null,
          "unit": "μW/cm²",
          "source_id": "S1",
          "evidence": "maximum output power density of 10.1 μW/cm2",
          "condition_text": "at a load resistance of 600 MΩ",
          "provenance": "author_result",
          "confidence": 0.98
        }}
      ],
      "notes": null
    }}


    如果找到范围，例如 120–960 pC/N：

    {{
      "found": true,
      "facts": [
        {{
          "value_type": "range",
          "value": null,
          "value_min": 120,
          "value_max": 960,
          "unit": "pC/N",
          "source_id": "S2",
          "evidence": "d33 piezoelectric coefficient ranging from 120 to 960 pC/N",
          "condition_text": null,
          "provenance": "cited_literature",
          "confidence": 0.95
        }}
      ],
      "notes": null
    }}


    如果没有找到目标指标：

    {{
      "found": false,
      "facts": [],
      "notes": "The target metric was not reliably reported in the provided evidence."
    }}
    """.strip()

    # ==========================
    # 构造 User Prompt
    # ==========================

    user_prompt = f"""
    以下内容是从当前这一篇论文中召回的候选片段：

    ---------------- 文献候选证据 ----------------

    {context}

    ---------------- 抽取任务 ----------------

    请抽取科研指标：

    {metric_spec.display_name}

    指标定义：

    {metric_spec.description}

    请严格按照 system prompt 中规定的 JSON 格式返回结果。
    """.strip()

    # ==========================
    # 4. 调用 DeepSeek
    # ==========================

    response = chat(
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0.0,
    )

    # ==========================
    # 5. JSON + Pydantic 校验
    # ==========================

    raw_data = parse_json_response(
        response
    )

    extraction_result = (
        LLMExtractionResult.model_validate(
            raw_data
        )
    )

    if not extraction_result.found:
        return []

    # ==========================
    # 6. 将 Source ID 映射回真实论文位置
    # ==========================

    final_facts = []

    for fact in extraction_result.facts:

        if fact.source_id not in source_map:
            print(
                f"警告：LLM 返回未知来源 "
                f"{fact.source_id}，已跳过。"
            )
            continue

        source = source_map[
            fact.source_id
        ]

        source_text = normalize_for_compare(
            source["text"]
        )

        evidence_text = normalize_for_compare(
            fact.evidence
        )

        # 检查 evidence 是否真的来自这个 Chunk
        evidence_verified = (
            evidence_text in source_text
        )

        final_facts.append(
            ExtractedFact(
                document_id=document_id,

                metric_name=metric_spec.key,

                value_type=fact.value_type,

                value=fact.value,

                value_min=fact.value_min,

                value_max=fact.value_max,

                unit=fact.unit,

                page_number=source["page_number"],

                chunk_id=source["chunk_id"],

                evidence=fact.evidence,

                evidence_verified=evidence_verified,

                condition_text=fact.condition_text,

                provenance=fact.provenance,

                confidence=fact.confidence,
            )
        )

    return final_facts