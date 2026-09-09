import pytest

import update_semantic_provenance


def make_row(
    row_id: int,
) -> dict:
    return {
        "id": row_id,
        "document_id": f"doc-{row_id}",
        "page_number": row_id,
        "raw_text": f"{row_id} V",
        "sentence_text": f"Sentence {row_id}",
        "context_text": f"Context {row_id}",
        "metric_key": "arbitrary_metric",
    }


class FakeClassification:
    def __init__(
        self,
        row_id: int,
    ):
        self.row_id = row_id

    def to_record(self) -> dict:
        return {
            "metric_classification_id":
                self.row_id,

            "provenance_classifier_version":
                update_semantic_provenance
                .SEMANTIC_PROVENANCE_CLASSIFIER_VERSION,

            "provenance_ontology_version":
                update_semantic_provenance
                .PROVENANCE_ONTOLOGY_VERSION,

            "status":
                "classified",

            "provenance":
                "author_result",

            "method":
                "llm",

            "score":
                None,

            "candidates_json":
                "[]",

            "reason":
                "semantic_classified: test",
        }


def install_fake_repository(
    monkeypatch,
    *,
    cached_rows: list[dict],
    pending_rows: list[dict],
):
    monkeypatch.setattr(
        update_semantic_provenance,
        "get_semantic_cache_rows",
        lambda **kwargs: list(
            cached_rows
        ),
    )

    monkeypatch.setattr(
        update_semantic_provenance,
        "get_semantic_pending_rows",
        lambda **kwargs: list(
            pending_rows
        ),
    )


def test_limit_caps_attempts_and_failures_are_not_cached(
    monkeypatch,
):
    pending_rows = [
        make_row(1),
        make_row(2),
        make_row(3),
    ]

    install_fake_repository(
        monkeypatch,
        cached_rows=[
            {
                "id": 100,
                "status": "classified",
                "provenance": "author_result",
            }
        ],
        pending_rows=pending_rows,
    )

    calls = []

    def fake_classify(row):
        calls.append(
            row["id"]
        )

        if row["id"] == 2:
            raise RuntimeError(
                "temporary API failure"
            )

        return FakeClassification(
            row["id"]
        )

    saved_records = []

    def fake_upsert(records):
        saved_records.extend(
            records
        )

    monkeypatch.setattr(
        update_semantic_provenance,
        "classify_semantic_provenance",
        fake_classify,
    )

    monkeypatch.setattr(
        update_semantic_provenance,
        "upsert_provenance_classifications",
        fake_upsert,
    )

    result = (
        update_semantic_provenance
        .update_semantic_provenance_cache(
            limit=2
        )
    )

    assert calls == [1, 2]

    assert len(saved_records) == 1

    assert (
        saved_records[0][
            "metric_classification_id"
        ]
        == 1
    )

    assert (
        result["total_semantic_targets"]
        == 4
    )

    assert (
        result["cached_semantic"]
        == 1
    )

    assert (
        result["attempted_now"]
        == 2
    )

    assert (
        result["successful_now"]
        == 1
    )

    assert (
        result["failed_now"]
        == 1
    )

    assert (
        result["completed_semantic"]
        == 2
    )

    assert (
        result["deferred_semantic"]
        == 2
    )

    assert (
        result["coverage_complete"]
        is False
    )


def test_successful_semantic_decisions_are_persisted_individually(
    monkeypatch,
):
    pending_rows = [
        make_row(1),
        make_row(2),
    ]

    install_fake_repository(
        monkeypatch,
        cached_rows=[],
        pending_rows=pending_rows,
    )

    monkeypatch.setattr(
        update_semantic_provenance,
        "classify_semantic_provenance",
        lambda row: FakeClassification(
            row["id"]
        ),
    )

    upsert_calls = []

    def fake_upsert(records):
        upsert_calls.append(
            list(records)
        )

    monkeypatch.setattr(
        update_semantic_provenance,
        "upsert_provenance_classifications",
        fake_upsert,
    )

    result = (
        update_semantic_provenance
        .update_semantic_provenance_cache()
    )

    assert len(upsert_calls) == 2

    assert all(
        len(call) == 1
        for call in upsert_calls
    )

    assert (
        result["attempted_now"]
        == 2
    )

    assert (
        result["successful_now"]
        == 2
    )

    assert (
        result["failed_now"]
        == 0
    )

    assert (
        result["completed_semantic"]
        == 2
    )

    assert (
        result["deferred_semantic"]
        == 0
    )

    assert (
        result["coverage_complete"]
        is True
    )


def test_invalid_limit_is_rejected():
    with pytest.raises(
        ValueError
    ):
        (
            update_semantic_provenance
            .update_semantic_provenance_cache(
                limit=0
            )
        )


def test_version_mismatch_is_rejected():
    with pytest.raises(
        ValueError
    ):
        (
            update_semantic_provenance
            .update_semantic_provenance_cache(
                semantic_classifier_version=(
                    "wrong-version"
                )
            )
        )
