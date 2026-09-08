from pathlib import Path

from sentence_transformers import SentenceTransformer


# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 本地 BGE-M3 模型目录
MODEL_PATH = PROJECT_ROOT / "models" / "bge-m3"

# 全局模型实例
_model = None


def get_embedding_model():
    """
    延迟加载本地 Embedding 模型。

    第一次调用时加载模型，
    后续重复使用同一个实例。
    """
    global _model

    if _model is None:
        print(f"正在加载本地 Embedding 模型：{MODEL_PATH}")

        _model = SentenceTransformer(
            str(MODEL_PATH),
            local_files_only=True,
        )

        print("Embedding 模型加载完成。")

    return _model


def embed_texts(texts: list[str]):
    """
    将一批文本转换为向量。
    """

    model = get_embedding_model()

    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    return vectors


def embed_query(query: str):
    """
    将用户查询转换为向量。
    """

    model = get_embedding_model()

    vector = model.encode(
        query,
        normalize_embeddings=True,
    )

    return vector