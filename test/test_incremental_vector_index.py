import pytest

import app.embedding.indexer as vector_indexer


@pytest.mark.integration
@pytest.mark.slow
def test_synced_vector_index_skips_embedding(
    monkeypatch,
) -> None:
    """
    验证增量向量索引的核心 no-op 行为。

    第一轮：

        SQLite ↔ Qdrant 如果存在差异，
        允许 build_vector_index() 自动修复。

    第二轮：

        索引已经同步。

        此时 embed_texts() 绝不能再次调用。

    使用真实：

    - SQLite
    - Qdrant

    如果第一轮存在缺失向量，
    可能加载 Embedding 模型。
    """

    # ========================================================
    # 1. 先确保索引同步
    # ========================================================

    first_result = (
        vector_indexer
        .build_vector_index()
    )

    assert (
        first_result.sqlite_count
        >= 0
    )

    # ========================================================
    # 2. 同步后禁止任何 Embedding
    # ========================================================

    def forbidden_embed(
        *args,
        **kwargs,
    ):
        raise AssertionError(
            "索引已经同步，"
            "但 embed_texts() "
            "仍然被调用。"
        )

    monkeypatch.setattr(
        vector_indexer,
        "embed_texts",
        forbidden_embed,
    )

    second_result = (
        vector_indexer
        .build_vector_index()
    )

    # ========================================================
    # 3. No-op Assertions
    # ========================================================

    assert (
        second_result.added_count
        == 0
    )

    assert (
        second_result.deleted_count
        == 0
    )

    assert (
        second_result.sqlite_count
        == second_result.qdrant_count_before
    )

    assert (
        second_result.unchanged_count
        == second_result.sqlite_count
    )