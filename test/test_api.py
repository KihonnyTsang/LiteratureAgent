from pathlib import (
    Path,
)

from unittest.mock import (
    patch,
)

from fastapi.testclient import (
    TestClient,
)

from app.agent.runtime_schemas import (
    AgentRunResult,
)

from app.api.server import (
    PLOTS_DIR,
    app,
)


client = TestClient(
    app
)


def build_structured_result(
    plot_path: str | None = None,
) -> AgentRunResult:
    """
    构造一个 synthetic structured Runtime Result。

    不调用：

    - Planner
    - DeepSeek
    - Embedding
    - Qdrant

    只测试 API Layer。
    """

    return AgentRunResult.model_validate(
        {
            "result_type":
                "structured",

            "plan": {
                "user_goal":
                    "测试结构化 API",

                "steps": [
                    {
                        "step_id":
                            "step_1",

                        "tool":
                            "query_metadata",

                        "arguments": {
                            "fields": [
                                "title",
                                "page_count",
                            ],

                            "scope":
                                "all_documents",
                        },

                        "description":
                            "测试步骤",
                    }
                ],

                "answer_mode":
                    (
                        "text_and_plot"
                        if plot_path
                        else "text"
                    ),
            },

            "markdown":
                "测试 structured response",

            "final_answer": {
                "summary":
                    "测试 structured response",

                "table_columns":
                    [],

                "table_rows":
                    [],

                "evidence_rows":
                    [],

                "plot_path":
                    plot_path,

                "warnings":
                    [],
            },

            "text_result":
                None,
        }
    )


def build_grounded_result() -> AgentRunResult:
    """
    构造 synthetic grounded-text result。
    """

    return AgentRunResult.model_validate(
        {
            "result_type":
                "grounded_text",

            "plan": {
                "user_goal":
                    "测试 RAG API",

                "steps": [
                    {
                        "step_id":
                            "step_1",

                        "tool":
                            "rag_search",

                        "arguments": {
                            "question":
                                "测试问题",

                            "top_k":
                                5,
                        },

                        "description":
                            "测试 RAG",
                    }
                ],

                "answer_mode":
                    "text",
            },

            "markdown":
                "依据文献[S1]进行回答。",

            "final_answer":
                None,

            "text_result": {
                "text":
                    "依据文献[S1]进行回答。",

                "sources": [
                    {
                        "source_id":
                            "S1",

                        "title":
                            "Test Paper",

                        "page_number":
                            1,

                        "chunk_index":
                            0,

                        "filename":
                            "test.pdf",

                        "local_path":
                            "/tmp/test.pdf",

                        "score":
                            0.9,
                    }
                ],

                "metadata": {
                    "result_kind":
                        "grounded_text",

                    "grounded":
                        True,

                    "source_count":
                        1,
                },
            },
        }
    )


def test_health() -> None:

    response = client.get(
        "/health"
    )

    assert (
        response.status_code
        == 200
    )

    body = response.json()

    assert (
        body["status"]
        == "ok"
    )

    assert (
        body["service"]
        == "LiteratureAgent"
    )


def test_empty_question() -> None:

    response = client.post(
        "/api/v1/agent/run",

        json={
            "question":
                "   ",
        },
    )

    assert (
        response.status_code
        == 422
    )


def test_structured_response() -> None:

    fake_result = (
        build_structured_result()
    )

    with patch(
        "app.api.routes.run_agent",
        return_value=fake_result,
    ):

        response = client.post(
            "/api/v1/agent/run",

            json={
                "question":
                    "测试 metadata",
            },
        )

    assert (
        response.status_code
        == 200
    )

    body = response.json()

    assert (
        body["result_type"]
        == "structured"
    )

    assert (
        body["final_answer"]
        is not None
    )

    assert (
        body["text_result"]
        is None
    )

    assert (
        body["plot_url"]
        is None
    )


def test_grounded_response() -> None:

    fake_result = (
        build_grounded_result()
    )

    with patch(
        "app.api.routes.run_agent",
        return_value=fake_result,
    ):

        response = client.post(
            "/api/v1/agent/run",

            json={
                "question":
                    "测试 RAG",
            },
        )

    assert (
        response.status_code
        == 200
    )

    body = response.json()

    assert (
        body["result_type"]
        == "grounded_text"
    )

    assert (
        body["final_answer"]
        is None
    )

    assert (
        body["text_result"]
        is not None
    )

    assert (
        body[
            "text_result"
        ][
            "sources"
        ][0][
            "source_id"
        ]
        == "S1"
    )


def test_plot_url() -> None:

    fake_plot = (
        PLOTS_DIR
        / "api_test_plot.png"
    )

    # StaticFiles 测试只需要确认
    # HTTP 文件映射成立。
    fake_plot.write_bytes(
        b"LiteratureAgent API "
        b"static test"
    )

    try:

        fake_result = (
            build_structured_result(
                plot_path=str(
                    fake_plot
                )
            )
        )

        with patch(
            "app.api.routes.run_agent",
            return_value=fake_result,
        ):

            response = client.post(
                "/api/v1/agent/run",

                json={
                    "question":
                        "测试 plot",
                },
            )

        assert (
            response.status_code
            == 200
        )

        body = response.json()

        plot_url = (
            body["plot_url"]
        )

        assert plot_url

        assert (
            plot_url.endswith(
                "/static/plots/"
                "api_test_plot.png"
            )
        )

        static_response = (
            client.get(
                "/static/plots/"
                "api_test_plot.png"
            )
        )

        assert (
            static_response.status_code
            == 200
        )

        assert (
            static_response.content
            == (
                b"LiteratureAgent API "
                b"static test"
            )
        )

    finally:

        if fake_plot.exists():

            fake_plot.unlink()


def main():

    test_health()

    print(
        "Health Test Passed"
    )

    test_empty_question()

    print(
        "Validation Test Passed"
    )

    test_structured_response()

    print(
        "Structured API Test Passed"
    )

    test_grounded_response()

    print(
        "Grounded API Test Passed"
    )

    test_plot_url()

    print(
        "Static Plot API Test Passed"
    )

    print()

    print(
        "=" * 80
    )

    print(
        "FastAPI Application Tests Passed"
    )

    print(
        "=" * 80
    )


if __name__ == "__main__":
    main()