import json
from dataclasses import dataclass
from typing import Any, Mapping

from app.enrichment.provenance_ontology import (
    PROVENANCE_ONTOLOGY_VERSION,
    rank_provenance_candidates,
)


PROVENANCE_CLASSIFIER_VERSION = (
    "provenance-classifier-v2"
)

MIN_PROVENANCE_SCORE = 1


@dataclass(frozen=True)
class ProvenanceClassification:
    metric_classification_id: int

    status: str

    provenance: str

    method: str

    score: int | None

    candidates_json: str

    reason: str

    provenance_classifier_version: str = (
        PROVENANCE_CLASSIFIER_VERSION
    )

    provenance_ontology_version: str = (
        PROVENANCE_ONTOLOGY_VERSION
    )

    def to_record(
        self,
    ) -> dict:

        return {
            "metric_classification_id":
                self.metric_classification_id,

            "provenance_classifier_version":
                self.provenance_classifier_version,

            "provenance_ontology_version":
                self.provenance_ontology_version,

            "status":
                self.status,

            "provenance":
                self.provenance,

            "method":
                self.method,

            "score":
                self.score,

            "candidates_json":
                self.candidates_json,

            "reason":
                self.reason,
        }


def _serialize_candidates(
    ranked: list[
        tuple[str, int]
    ],
) -> str:

    payload = [
        {
            "provenance":
                provenance,

            "score":
                score,
        }
        for (
            provenance,
            score,
        )
        in ranked
    ]

    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(
            ",",
            ":",
        ),
    )


def classify_provenance(
    row: Mapping[
        str,
        Any,
    ],
) -> ProvenanceClassification:
    """
    Deterministic provenance classifier.

    重要：
    本函数不知道 metric 是什么。
    """

    metric_classification_id = int(
        row["id"]
    )

    sentence_text = (
        row.get(
            "sentence_text"
        )
        or ""
    )

    context_text = (
        row.get(
            "context_text"
        )
        or ""
    )

    if (
        context_text
        and
        context_text
        != sentence_text
    ):

        text = (
            sentence_text
            + " "
            + context_text
        )

    else:

        text = sentence_text

    ranked = (
        rank_provenance_candidates(
            text
        )
    )

    candidates_json = (
        _serialize_candidates(
            ranked
        )
    )

    if not ranked:

        return ProvenanceClassification(
            metric_classification_id=(
                metric_classification_id
            ),

            status="unresolved",

            provenance="uncertain",

            method="deterministic",

            score=None,

            candidates_json="[]",

            reason=(
                "no_provenance_candidates"
            ),
        )

    top_key, top_score = (
        ranked[0]
    )

    if (
        top_score
        < MIN_PROVENANCE_SCORE
    ):

        return ProvenanceClassification(
            metric_classification_id=(
                metric_classification_id
            ),

            status="unresolved",

            provenance="uncertain",

            method="deterministic",

            score=top_score,

            candidates_json=(
                candidates_json
            ),

            reason=(
                "insufficient_provenance_context"
            ),
        )

    if len(ranked) > 1:

        second_score = (
            ranked[1][1]
        )

        if (
            second_score
            == top_score
        ):

            return ProvenanceClassification(
                metric_classification_id=(
                    metric_classification_id
                ),

                status="unresolved",

                provenance="uncertain",

                method="deterministic",

                score=top_score,

                candidates_json=(
                    candidates_json
                ),

                reason=(
                    "tied_provenance_candidates"
                ),
            )

    return ProvenanceClassification(
        metric_classification_id=(
            metric_classification_id
        ),

        status="classified",

        provenance=top_key,

        method="deterministic",

        score=top_score,

        candidates_json=(
            candidates_json
        ),

        reason=(
            "unique_positive_provenance"
        ),
    )