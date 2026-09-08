import json
import re

from app.extraction.schemas import MetricSpec
from app.extraction.metric_registry import (
    METRIC_REGISTRY,
)
from app.llm.siliconflow_client import chat


def parse_json_response(
    response: str,
) -> dict:

    text = response.strip()

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

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(
            "MetricSpec 生成结果中没有找到 JSON。"
        )

    return json.loads(
        text[start:end + 1]
    )


def generate_metric_spec(
    metric_text: str,
) -> MetricSpec:
    """
    对 Registry 中不存在的科研指标，
    让 LLM 动态生成 MetricSpec。
    """

    system_prompt = """
你是科研文献数据抽取系统中的指标定义器。

用户会提供一个科研指标名称。

你的任务是把它转换为适用于科研论文检索和数据抽取的
结构化 MetricSpec。

要求：

1. key 使用简洁、稳定的英文 snake_case。

2. display_name 保留科研领域常用名称。

3. description 必须明确该指标的物理含义，
   以便后续模型区分相似指标。

4. search_queries 提供 3～6 个英文论文中常见表达。

5. canonical_unit 指定后续数据库和统计使用的推荐标准单位。

例如：

功率密度：
W/m²

储能密度：
J/cm³

击穿场强：
MV/m

d33：
pC/N

输出电压：
V

6. exclude_terms 列出容易与目标指标混淆的概念。

7. 不需要回答该指标的具体数值。

只能返回 JSON，不输出 Markdown。

格式：

{
  "key": "piezoelectric_coefficient_d33",
  "display_name": "压电系数 d33",
  "description": "...",
  "search_queries": [
    "piezoelectric coefficient d33",
    "d33 coefficient"
  ],
  "canonical_unit": "pC/N",
  "valid_units": [
    "pC/N",
    "nC/N",
    "pm/V"
  ],
  "exclude_terms": [
    "d31"
  ]
}
""".strip()

    user_prompt = f"""
用户希望提取的科研指标：

{metric_text}

请生成 MetricSpec。
""".strip()

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

    raw_data = parse_json_response(
        response
    )

    return MetricSpec.model_validate(
        raw_data
    )


def resolve_metric_spec(
    metric_name: str | None,
    metric_text: str | None,
) -> MetricSpec:
    """
    优先使用 Registry。

    如果 Registry 中没有，
    则根据用户原始表达动态生成 MetricSpec。
    """

    if (
        metric_name is not None
        and metric_name in METRIC_REGISTRY
    ):
        return METRIC_REGISTRY[
            metric_name
        ]

    if metric_text:
        return generate_metric_spec(
            metric_text
        )

    raise ValueError(
        "无法确定需要提取的科研指标。"
    )