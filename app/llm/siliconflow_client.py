import os

from dotenv import load_dotenv
from openai import OpenAI


# 读取项目根目录中的 .env
load_dotenv()


API_KEY = os.getenv("SILICONFLOW_API_KEY")

BASE_URL = "https://api.siliconflow.cn/v1"

DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4-Flash"


if not API_KEY:
    raise RuntimeError(
        "没有找到 SILICONFLOW_API_KEY，"
        "请检查项目根目录中的 .env 文件。"
    )


client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
)


def chat(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.1,
) -> str:
    """
    调用 SiliconFlow 上的 LLM。
    """

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )

    return response.choices[0].message.content