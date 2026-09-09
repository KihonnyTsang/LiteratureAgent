import json

import pytest

from pydantic import ValidationError

from app.enrichment import (
    semantic_provenance_classifier,
)

from app.enrichment.semantic_provenance_classifier import (
    SEMANTIC_PROVENANCE_CLASSIFIER_VERSION,
    SemanticProvenanceDecision,
    build_semantic_provenance_messages,
    classify_semantic_provenance,
    parse_semantic_provenance_response,
)


def make_row(
    *,
    row_id: int = 1,
    raw_text: str = "12.3 V",
    sentence_text: str = (
        "The measured value was 12.3 V."
    ),
    context_text: str = (
        "The measured value was 12.3 V."
    ),
) -> dict:

    return {
        "id":
            row_id,

        "raw_text":
            raw_text,

        "sentence_text":
            sentence_text,

        "context_text":
            context_text,

        # Semantic provenance must not depend on metric_key.
        "metric_key":
            "arbitrary_metric",
    }


def install_fake_chat(
    monkeypatch,
    *,
    response: str,
):

    calls = []

    def fake_chat(
        messages,
        model=None,
        temperature=0.1,
    ):

        calls.append(
            {
                "messages":
                    messages,

                "model":
                    model,

                "temperature":
                    temperature,
            }
        )

        return response

    monkeypatch.setattr(
        semantic_provenance_classifier,
        "chat",
        fake_chat,
    )

    return calls


def test_semantic_author_result_requires_explicit_current_work(
    monkeypatch,
):

    calls = install_fake_chat(
        monkeypatch,

        response=json.dumps(
            {
                "provenance":
                    "author_result",

                "ownership_evidence":
                    "explicit_current_work",

                "confidence":
                    0.94,

                "reason":
                    (
                        "The target result is "
                        "explicitly linked to "
                        "the current study."
                    ),
            }
        ),
    )

    result = (
        classify_semantic_provenance(
            make_row()
        )
    )

    assert result.status == "classified"
    assert result.provenance == "author_result"
    assert result.method == "llm"
    assert result.score is None

    assert (
        result.provenance_classifier_version
        ==
        SEMANTIC_PROVENANCE_CLASSIFIER_VERSION
    )

    assert len(calls) == 1
    assert calls[0]["temperature"] == 0.0


def test_semantic_cited_literature_requires_external_attribution(
    monkeypatch,
):

    install_fake_chat(
        monkeypatch,

        response=json.dumps(
            {
                "provenance":
                    "cited_literature",

                "ownership_evidence":
                    "explicit_external_attribution",

                "confidence":
                    0.98,

                "reason":
                    (
                        "The target value is "
                        "explicitly attributed "
                        "to another study."
                    ),
            }
        ),
    )

    result = (
        classify_semantic_provenance(
            make_row()
        )
    )

    assert result.status == "classified"
    assert result.provenance == "cited_literature"


def test_semantic_uncertain_abstains(
    monkeypatch,
):

    install_fake_chat(
        monkeypatch,

        response=json.dumps(
            {
                "provenance":
                    "uncertain",

                "ownership_evidence":
                    "insufficient",

                "confidence":
                    0.55,

                "reason":
                    (
                        "Ownership cannot be "
                        "established from the "
                        "local evidence."
                    ),
            }
        ),
    )

    result = (
        classify_semantic_provenance(
            make_row()
        )
    )

    assert result.status == "unresolved"
    assert result.provenance == "uncertain"
    assert result.method == "llm"


def test_author_label_without_current_work_evidence_is_guarded(
    monkeypatch,
):

    install_fake_chat(
        monkeypatch,

        response=json.dumps(
            {
                "provenance":
                    "author_result",

                "ownership_evidence":
                    "insufficient",

                "confidence":
                    0.92,

                "reason":
                    (
                        "No external citation "
                        "was visible."
                    ),
            }
        ),
    )

    result = (
        classify_semantic_provenance(
            make_row()
        )
    )

    assert result.status == "unresolved"
    assert result.provenance == "uncertain"

    assert (
        result.reason.startswith(
            "semantic_guard_rejected:"
        )
    )


def test_cited_label_without_external_evidence_is_guarded(
    monkeypatch,
):

    install_fake_chat(
        monkeypatch,

        response=json.dumps(
            {
                "provenance":
                    "cited_literature",

                "ownership_evidence":
                    "explicit_current_work",

                "confidence":
                    0.9,

                "reason":
                    "Inconsistent model output.",
            }
        ),
    )

    result = (
        classify_semantic_provenance(
            make_row()
        )
    )

    assert result.status == "unresolved"
    assert result.provenance == "uncertain"

    assert (
        result.reason.startswith(
            "semantic_guard_rejected:"
        )
    )


def test_markdown_json_fence_is_tolerated():

    raw_data = (
        parse_semantic_provenance_response(
            """
```json
{
  "provenance": "author_result",
  "ownership_evidence": "explicit_current_work",
  "confidence": 0.9,
  "reason": "Explicit ownership."
}
```
"""
        )
    )

    decision = (
        SemanticProvenanceDecision.model_validate(
            raw_data
        )
    )

    assert decision.provenance == "author_result"

    assert (
        decision.ownership_evidence
        == "explicit_current_work"
    )

    assert decision.confidence == 0.9


def test_invalid_provenance_is_rejected():

    with pytest.raises(
        ValidationError
    ):

        SemanticProvenanceDecision.model_validate(
            {
                "provenance":
                    "probably_author",

                "ownership_evidence":
                    "explicit_current_work",

                "confidence":
                    0.9,

                "reason":
                    "Invalid enum.",
            }
        )


def test_invalid_ownership_evidence_is_rejected():

    with pytest.raises(
        ValidationError
    ):

        SemanticProvenanceDecision.model_validate(
            {
                "provenance":
                    "author_result",

                "ownership_evidence":
                    "absence_of_citation",

                "confidence":
                    0.9,

                "reason":
                    "Invalid evidence enum.",
            }
        )


def test_prompt_is_metric_agnostic_and_rejects_absence_inference():

    row = make_row(
        raw_text=(
            "7.5 arbitrary_unit"
        )
    )

    messages = (
        build_semantic_provenance_messages(
            row
        )
    )

    rendered = "\n".join(
        message["content"]
        for message
        in messages
    )

    assert (
        "7.5 arbitrary_unit"
        in rendered
    )

    assert (
        "arbitrary_metric"
        not in rendered
    )

    assert (
        "NOT evidence"
        in rendered
    )
