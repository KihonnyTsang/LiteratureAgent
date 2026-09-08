from app.rag.retriever import semantic_search
from app.llm.siliconflow_client import chat
import re

def build_context(results: list[dict]) -> str:
    """
    将检索到的文献 Chunk 整理成 LLM 可以阅读的 Context。
    """

    context_parts = []

    for index, result in enumerate(results, start=1):
        source_id = f"S{index}"

        context = f"""
[{source_id}]
文献：{result["title"]}
页码：{result["page_number"]}
Chunk：{result["chunk_index"]}

{result["text"]}
""".strip()

        context_parts.append(context)

    return "\n\n".join(context_parts)


def answer_question(
    question: str,
    top_k: int = 5,
) -> dict:
    """
    根据本地文献知识库回答问题。
    """

    # ==========================
    # 1. 从 Qdrant 检索相关内容
    # ==========================

    results = semantic_search(
        query=question,
        top_k=top_k,
    )

    if not results:
        return {
            "answer": "知识库中没有检索到相关内容。",
            "sources": [],
        }

    # ==========================
    # 2. 构造上下文
    # ==========================

    context = build_context(results)

    # ==========================
    # 3. System Prompt
    # ==========================

    system_prompt = """
你是一名严谨的科研文献助手。

你的任务是严格依据用户本地文献库中检索到的文献片段回答科研问题。

必须遵守以下规则：

1. 只能依据提供的文献片段回答。
2. 不要使用文献片段之外的知识补充事实。
3. 不允许编造实验数据、数值、材料性能、作者观点或结论。
4. 如果当前文献片段不足以回答问题，请明确说明：
   “根据当前检索到的文献内容无法确定。”
5. 每个重要结论都应尽可能标注文献片段编号，例如 [S1]、[S2]。
6. 如果多个片段互相补充，可以综合回答并同时引用，例如 [S1][S3]。
7. 优先使用中文回答，必要的专业术语可以保留英文。
8. 回答应简洁、准确、有科研表达风格。
""".strip()

    # ==========================
    # 4. User Prompt
    # ==========================

    user_prompt = f"""
以下内容来自我的本地科研文献知识库：

---------------- 文献内容 ----------------

{context}

---------------- 用户问题 ----------------

{question}

请严格依据上述文献内容回答，并标注信息来源。
""".strip()

    # ==========================
    # 5. 调用 SiliconFlow LLM
    # ==========================

    answer = chat(
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ]
    )

    # 找出回答中真正引用过的 Source ID
    cited_source_ids = set(
        re.findall(r"\[(S\d+)\]", answer)
    )

    # ==========================
    # 6. 整理来源
    # ==========================

    sources = []

    for index, result in enumerate(
            results,
            start=1,
    ):
        source_id = f"S{index}"

        # 只返回 LLM 实际引用的来源
        if source_id not in cited_source_ids:
            continue

        sources.append(
            {
                "source_id": source_id,
                "title": result["title"],
                "page_number": result["page_number"],
                "chunk_index": result["chunk_index"],
                "filename": result["filename"],
                "local_path": result["local_path"],
                "score": result["score"],
            }
        )

    return {
        "answer": answer,
        "sources": sources,
    }