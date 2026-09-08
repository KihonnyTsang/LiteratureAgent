import json
import re

from app.agent.plan_schemas import (
    AgentPlan,
)

from app.llm.siliconflow_client import (
    chat,
)


TOOL_CATALOG = """
你可以使用以下工具：

==================================================
1. rag_search
==================================================

用途：
基于本地文献全文进行语义检索，
并回答需要阅读论文内容才能回答的问题。

适合：

- 为什么某种材料处理会增强性能？
- 某篇论文如何解释某个机制？
- 作者如何描述某种现象？
- 某种结构设计为什么有效？
- 文献中如何讨论某个科研问题？

参数：

{
  "question": "用户需要回答的完整问题",
  "top_k": 5
}

question 必须保留用户问题的完整语义。

top_k 默认使用 5。


不要使用 rag_search 执行：

- 跨论文定量排序
- 最大值 / 最小值
- 平均值
- 单位归一化后的比较
- 跨所有论文的结构化科研指标统计

这些任务应该使用：

query_facts
query_metadata
aggregate_table
sort_table
plot_table


==================================================
2. query_facts
==================================================

用途：
获取论文中的结构化科研指标。

适合：

- 功率密度
- 输出电压
- 储能密度
- 击穿场强
- d33
- 其他科研数值指标

metric 可以是系统以前没有见过的新科研指标。

参数示例：

{
  "metric": "功率密度",
  "scope": "all_documents",
  "provenance_scope": "author_results"
}


query_facts 返回统一表格字段：

document_id
title

value
value_min
value_max
unit

raw_value
raw_value_min
raw_value_max
raw_unit

value_type
page_number
condition_text
evidence
provenance
confidence


非常重要：

value
=
已经进行单位归一化、
可以用于跨论文数学比较的标准数值。

unit
=
value 对应的标准单位。


raw_value
raw_unit
=
论文原始报告的数值和单位。


因此：

排序、max、min、mean、绘图等数学操作，
必须优先使用：

"value"

不要使用：

"raw_value"

也不要使用：

"normalized_value"

因为 query_facts 的标准数学字段统一叫：

"value"


一篇论文可能返回多条 Fact。

例如同一篇论文可能在不同实验条件下
报告两个功率密度。

因此如果用户要求：

“比较每篇论文的功率密度”
“哪篇论文功率密度最高”
“每篇论文取一个代表值”

通常应该先：

aggregate_table

group_by：

[
  "document_id",
  "title"
]

field：

"value"

operation：

"max"

然后再：

sort_table
或
plot_table。


==================================================
3. query_metadata
==================================================

用途：
查询论文文件和数据库本身已经保存的元数据。

当前可用字段：

- id
- title
- filename
- local_path
- page_count

适合：

- 每篇论文多少页
- 文件名
- 本地 PDF 路径
- 文档列表

参数示例：

{
  "fields": [
    "title",
    "page_count"
  ],
  "scope": "all_documents"
}


==================================================
4. filter_table
==================================================

用途：
对上一步产生的表格进行筛选。

参数示例：

{
  "input_step": "step_1",
  "conditions": [
    {
      "field": "normalized_value",
      "operator": ">",
      "value": 1
    }
  ]
}


==================================================
5. aggregate_table
==================================================

用途：
对表格进行确定性数值统计。

支持常见操作：

- max
- min
- mean
- median
- sum
- count

也支持 group_by。

参数示例：

{
  "input_step": "step_1",
  "group_by": "document_id",
  "field": "normalized_value",
  "operation": "max"
}

aggregate_table 的统计结果统一放在字段：

"value"

例如：

{
  "input_step": "step_1",
  "field": "page_count",
  "operation": "mean"
}

返回：

{
  "value": 12.875
}


group_by 可以是一个字段：

"document_id"

也可以是多个字段：

[
  "document_id",
  "title"
]

例如：

{
  "input_step": "step_1",
  "group_by": [
    "document_id",
    "title"
  ],
  "field": "value",
  "operation": "max"
}

==================================================
6. sort_table
==================================================

用途：
对表格按字段排序。

参数示例：

{
  "input_step": "step_2",
  "field": "normalized_value",
  "order": "descending"
}


==================================================
7. plot_table
==================================================

用途：
把某一步产生的表格绘制成图。

支持：

- bar
- line
- scatter
- pie

参数示例：

{
  "input_step": "step_2",
  "chart_type": "bar",
  "x": "title",
  "y": "page_count",
  "title": "各论文页数比较"
}
""".strip()


def parse_json_response(
    response: str,
) -> dict:
    """
    从 LLM 返回内容中提取 JSON。
    """

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

    if (
        start == -1
        or end == -1
    ):
        raise ValueError(
            "Planner 返回内容中没有找到 JSON。"
        )

    return json.loads(
        text[start:end + 1]
    )

def infer_answer_mode(
    steps: list[dict],
) -> str:
    """
    根据 Planner 选择的工具，
    由 Python 确定最终输出形式。

    不依赖 LLM 自己填写 answer_mode。
    """

    tools = {
        step.get("tool")
        for step in steps
    }

    # 有绘图任务：
    # 最终既展示文字，也展示数据表和图。
    if "plot_table" in tools:
        return "text_table_and_plot"

    # 数据查询 / 数据处理任务：
    # 最终展示文字 + 表格。
    table_tools = {
        "query_facts",
        "query_metadata",
        "filter_table",
        "aggregate_table",
        "sort_table",
    }

    if tools & table_tools:
        return "text_and_table"

    # 普通 RAG：
    # 直接文本回答。
    return "text"

def create_plan(
    question: str,
) -> AgentPlan:
    """
    根据用户自然语言生成工具执行计划。

    注意：
    这里只规划，不执行。
    """

    system_prompt = """
    你是 LiteratureAgent 的任务规划器。

    你的职责不是直接回答用户问题。

    你的职责是：

    把用户自然语言请求拆解成一个
    可以由工具顺序执行的计划。

    当前系统提供以下工具：

    __TOOL_CATALOG__


    ==================================================
    规划原则
    ==================================================

    1. 不要为用户问题编造数据。


    2. 如果数据已经存在于文档元数据数据库中，
    优先使用 query_metadata。

    例如：

    “统计所有论文页数”
    必须使用 query_metadata，
    不能使用 rag_search 或 query_facts。


    3. 如果用户要求科研实验指标：

    例如：

    功率密度
    d33
    击穿场强
    输出电压
    储能密度

    优先使用 query_facts。


    4. 如果用户问：

    为什么
    什么机制
    作者如何解释
    论文主要做了什么

    使用 rag_search。


    5. 绘图本身必须使用 plot_table。

    不要让 LLM 自己假装生成图表。


    6. max、min、mean、median、sum、count、
    排序等确定性数学操作，

    必须使用：

    aggregate_table
    sort_table

    不要让 LLM 自己心算。


    7. 一个问题可以包含多个步骤。

    例如：

    “比较所有论文的功率密度并画图”

    可以规划为：

    query_facts
    → aggregate_table
    → sort_table
    → plot_table


    8. 后一步需要使用前一步结果时，
    arguments 中使用：

    "input_step": "step_1"

    例如：

    {
      "step_id": "step_2",
      "tool": "sort_table",
      "arguments": {
        "input_step": "step_1",
        "field": "normalized_value",
        "order": "descending"
      },
      "description": "按照标准化数值从高到低排序"
    }


    9. step_id 必须按照顺序：

    step_1
    step_2
    step_3
    step_4


    10. 不要因为系统没有预先列出某个科研指标，
    就拒绝使用 query_facts。

    例如：

    d33
    pyroelectric coefficient
    dielectric constant

    都可以直接作为 metric 文本
    传给 query_facts。


    11. 如果用户要求：

    “包括引用数据”
    “包括其他文献引用的数据”
    “论文中出现过的所有数据”

    则 query_facts 应使用：

    "provenance_scope": "all_mentions"

    如果用户只要求论文作者自己的结果，
    或者没有特别说明：

    "provenance_scope": "author_results"


    12. query_metadata 只用于数据库中已经存在的
    文档自身信息。

    例如：

    title
    filename
    local_path
    page_count


    13. query_facts 用于需要从论文内容中提取的
    科研指标。

    不要用 query_facts 获取 page_count。


    14. 如果用户只是普通文献问答，
    不要无意义地增加 aggregate_table、
    sort_table 或 plot_table。

    15. 对于 query_facts 返回的数据：

    数学分析统一使用字段：

    "value"


    16. 如果一篇论文可能存在多个目标指标结果，
    而用户希望跨论文比较一个代表值，

    必须先使用 aggregate_table 按：

    document_id
    title

    分组。

    例如：

    “比较所有论文的功率密度并画图”

    推荐计划：

    query_facts
    → aggregate_table(
        group_by=["document_id", "title"],
        field="value",
        operation="max"
    )
    → plot_table


    17. 如果用户还明确要求排序：

    query_facts
    → aggregate_table
    → sort_table
    → plot_table

    ==================================================
    输出规则
    ==================================================

    answer_mode 可以返回任意占位值。

    最终输出模式由执行系统根据 tools 自动确定，

    不要依赖 answer_mode 进行任务规划。

    你必须只返回合法 JSON。

    不要输出 Markdown。

    不要回答用户问题。

    不要在 JSON 前后添加解释。


    返回格式：

    {
      "user_goal": "用户希望完成的任务",
      "steps": [
        {
          "step_id": "step_1",
          "tool": "query_metadata",
          "arguments": {
            "fields": [
              "title",
              "page_count"
            ],
            "scope": "all_documents"
          },
          "description": "读取所有论文的页数"
        },
        {
          "step_id": "step_2",
          "tool": "plot_table",
          "arguments": {
            "input_step": "step_1",
            "chart_type": "bar",
            "x": "title",
            "y": "page_count",
            "title": "各论文页数比较"
          },
          "description": "绘制论文页数柱状图"
        }
      ],
      "answer_mode": "text_table_and_plot"
    }
    """.strip()

    system_prompt = system_prompt.replace(
        "__TOOL_CATALOG__",
        TOOL_CATALOG,
    )

    user_prompt = f"""
用户请求：

{question}

请生成工具执行计划。
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

    # ============================================================
    # answer_mode 不由 LLM 决定
    # ============================================================

    steps = raw_data.get(
        "steps",
        []
    )

    raw_data["answer_mode"] = (
        infer_answer_mode(
            steps
        )
    )

    return AgentPlan.model_validate(
        raw_data
    )