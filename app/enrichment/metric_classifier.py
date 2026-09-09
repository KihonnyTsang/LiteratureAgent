import json
from dataclasses import dataclass
from typing import Any, Mapping

from app.enrichment.metric_ontology import (
    ONTOLOGY_VERSION,
    rank_metric_candidates,
)

from app.enrichment.unit_signature import (
    NORMALIZER_VERSION,
)


CLASSIFIER_VERSION = (
    "metric-classifier-v1"
)

MIN_DETERMINISTIC_SCORE = 1


@dataclass(frozen=True)
class MetricClassification:
    mention_id: int

    status: str

    metric_key: str | None

    method: str

    score: int | None

    candidates_json: str

    reason: str

    classifier_version: str = (
        CLASSIFIER_VERSION
    )

    ontology_version: str = (
        ONTOLOGY_VERSION
    )

    normalizer_version: str = (
        NORMALIZER_VERSION
    )

    def to_record(
        self,
    ) -> dict:
        return {
            "mention_id":
                self.mention_id,

            "classifier_version":
                self.classifier_version,

            "ontology_version":
                self.ontology_version,

            "normalizer_version":
                self.normalizer_version,

            "status":
                self.status,

            "metric_key":
                self.metric_key,

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
            "metric_key":
                metric_key,

            "score":
                score,
        }
        for (
            metric_key,
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


def classify_numeric_mention(
    mention: Mapping[
        str,
        Any,
    ],
) -> MetricClassification:
    """
    Deterministic Metric Classifier v1.

    Numeric Mention
        ↓
    dimensionality candidate routing
        ↓
    deterministic lexical ranking
        ↓
    classified / unresolved / rejected

    本函数永远不调用 LLM。
    """

    mention_id = int(
        mention["id"]
    )

    raw_unit = (
        mention.get(
            "raw_unit"
        )
        or ""
    ).strip()

    if not raw_unit:

        return MetricClassification(
            mention_id=mention_id,

            status="rejected",

            metric_key=None,

            method="deterministic",

            score=None,

            candidates_json="[]",

            reason="missing_unit",
        )

    text = (
        mention.get(
            "sentence_text"
        )
        or
        mention.get(
            "context_text"
        )
        or
        ""
    )

    ranked = (
        rank_metric_candidates(
            raw_unit=raw_unit,
            text=text,
        )
    )

    candidates_json = (
        _serialize_candidates(
            ranked
        )
    )

    if not ranked:

        return MetricClassification(
            mention_id=mention_id,

            status="rejected",

            metric_key=None,

            method="deterministic",

            score=None,

            candidates_json=(
                candidates_json
            ),

            reason=(
                "no_supported_metric_candidate"
            ),
        )

    top_key, top_score = (
        ranked[0]
    )

    if (
        top_score
        < MIN_DETERMINISTIC_SCORE
    ):

        return MetricClassification(
            mention_id=mention_id,

            status="unresolved",

            metric_key=None,

            method="deterministic",

            score=top_score,

            candidates_json=(
                candidates_json
            ),

            reason=(
                "insufficient_context"
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

            return MetricClassification(
                mention_id=mention_id,

                status="unresolved",

                metric_key=None,

                method="deterministic",

                score=top_score,

                candidates_json=(
                    candidates_json
                ),

                reason=(
                    "tied_top_candidates"
                ),
            )

    return MetricClassification(
        mention_id=mention_id,

        status="classified",

        metric_key=top_key,

        method="deterministic",

        score=top_score,

        candidates_json=(
            candidates_json
        ),

        reason=(
            "unique_positive_candidate"
        ),
    )