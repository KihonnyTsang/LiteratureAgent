import json

import pytest

from pydantic import ValidationError

from app.enrichment import semantic_provenance_classifier
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
    sentence_text: str = "The measured value was 12.3 V.",
    context_text: str = "The measured value was 12.3 V.",
) -> dict:
    return {
        "id": row_id,
        "raw_text": raw_text,
        "sentence_text": sentence_text,
        "context_text": context_text,
        "metric_key": "arbitrary_metric",
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
                "messages": messages,
                "model": model,
                "temperature": temperature,
            }
        )
        return response

    monkeypatch.setattr(
        semantic_provenance_classifier,
        "chat",
        fake_chat,
    )

    return calls


def test_semantic_author_result(monkeypatch):
    calls = install_fake_chat(
        monkeypatch,
        response=json.dumps(
            {
                "provenance": "author_result",
                "confidence": 0.94,
                "reason": "The passage attributes the result to the current study.",
            }
        ),
    )

    result = classify_semantic_provenance(
        make_row()
    )

    assert result.status == "classified"
    assert result.provenance == "author_result"
    assert result.method == "llm"
    assert result.score is None
    assert (
        result.provenance_classifier_version
        == SEMANTIC_PROVENANCE_CLASSIFIER_VERSION
    )

    assert len(calls) == 1
    assert calls[0]["temperature"] == 0.0


def test_semantic_cited_literature(monkeypatch):
    install_fake_chat(
        monkeypatch,
        response=json.dumps(
            {
                "provenance": "cited_literature",
                "confidence": 0.98,
                "reason": "The value is explicitly attributed to another study.",
            }
        ),
    )

    result = classify_semantic_provenance(
        make_row()
    )

    assert result.status == "classified"
    assert result.provenance == "cited_literature"
    assert result.method == "llm"
    assert result.score is None


def test_semantic_uncertain_abstains(monkeypatch):
    install_fake_chat(
        monkeypatch,
        response=json.dumps(
            {
                "provenance": "uncertain",
                "confidence": 0.55,
                "reason": "Ownership cannot be established from the local evidence.",
            }
        ),
    )

    result = classify_semantic_provenance(
        make_row()
    )

    assert result.status == "unresolved"
    assert result.provenance == "uncertain"
    assert result.method == "llm"
    assert result.score is None


def test_markdown_json_fence_is_tolerated():
    raw_data = parse_semantic_provenance_response(
        '''
```json
{
  "provenance": "author_result",
  "confidence": 0.9,
  "reason": "Explicit ownership."
}
```
'''
    )

    decision = SemanticProvenanceDecision.model_validate(
        raw_data
    )

    assert decision.provenance == "author_result"
    assert decision.confidence == 0.9
    assert decision.reason == "Explicit ownership."


def test_invalid_provenance_is_rejected():
    with pytest.raises(ValidationError):
        SemanticProvenanceDecision.model_validate(
            {
                "provenance": "probably_author",
                "confidence": 0.9,
                "reason": "Invalid enum.",
            }
        )


def test_prompt_is_metric_agnostic():
    row = make_row(
        raw_text="7.5 arbitrary_unit"
    )

    messages = build_semantic_provenance_messages(
        row
    )

    rendered = "\n".join(
        message["content"]
        for message in messages
    )

    assert "7.5 arbitrary_unit" in rendered
    assert "arbitrary_metric" not in rendered
