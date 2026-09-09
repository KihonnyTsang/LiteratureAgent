import argparse
from collections import Counter

from app.database.sqlite_db import init_db

from app.database.enrichment_repository import (
    get_pending_semantic_provenance_input_rows,
    get_provenance_classification_rows,
    upsert_provenance_classifications,
)

from app.enrichment.metric_classifier import CLASSIFIER_VERSION
from app.enrichment.metric_ontology import ONTOLOGY_VERSION
from app.enrichment.numeric_scanner import DETECTOR_VERSION
from app.enrichment.provenance_classifier import (
    PROVENANCE_CLASSIFIER_VERSION,
)
from app.enrichment.provenance_ontology import (
    PROVENANCE_ONTOLOGY_VERSION,
)
from app.enrichment.semantic_provenance_classifier import (
    SEMANTIC_PROVENANCE_CLASSIFIER_VERSION,
    classify_semantic_provenance,
)
from app.enrichment.unit_signature import NORMALIZER_VERSION


def _validate_active_versions(
    *,
    detector_version: str,
    metric_classifier_version: str,
    metric_ontology_version: str,
    normalizer_version: str,
    deterministic_classifier_version: str,
    provenance_ontology_version: str,
    semantic_classifier_version: str,
) -> None:
    if detector_version != DETECTOR_VERSION:
        raise ValueError(
            "detector_version does not match the active implementation: "
            f"{detector_version!r} != {DETECTOR_VERSION!r}"
        )

    if metric_classifier_version != CLASSIFIER_VERSION:
        raise ValueError(
            "metric_classifier_version does not match the active implementation: "
            f"{metric_classifier_version!r} != {CLASSIFIER_VERSION!r}"
        )

    if metric_ontology_version != ONTOLOGY_VERSION:
        raise ValueError(
            "metric_ontology_version does not match the active implementation: "
            f"{metric_ontology_version!r} != {ONTOLOGY_VERSION!r}"
        )

    if normalizer_version != NORMALIZER_VERSION:
        raise ValueError(
            "normalizer_version does not match the active implementation: "
            f"{normalizer_version!r} != {NORMALIZER_VERSION!r}"
        )

    if deterministic_classifier_version != PROVENANCE_CLASSIFIER_VERSION:
        raise ValueError(
            "deterministic_classifier_version does not match the active implementation: "
            f"{deterministic_classifier_version!r} != "
            f"{PROVENANCE_CLASSIFIER_VERSION!r}"
        )

    if provenance_ontology_version != PROVENANCE_ONTOLOGY_VERSION:
        raise ValueError(
            "provenance_ontology_version does not match the active implementation: "
            f"{provenance_ontology_version!r} != "
            f"{PROVENANCE_ONTOLOGY_VERSION!r}"
        )

    if semantic_classifier_version != SEMANTIC_PROVENANCE_CLASSIFIER_VERSION:
        raise ValueError(
            "semantic_classifier_version does not match the active implementation: "
            f"{semantic_classifier_version!r} != "
            f"{SEMANTIC_PROVENANCE_CLASSIFIER_VERSION!r}"
        )


def get_semantic_cache_rows(
    *,
    detector_version: str,
    metric_classifier_version: str,
    metric_ontology_version: str,
    normalizer_version: str,
    semantic_classifier_version: str,
    provenance_ontology_version: str,
) -> list[dict]:
    return get_provenance_classification_rows(
        detector_version=detector_version,
        metric_classifier_version=metric_classifier_version,
        ontology_version=metric_ontology_version,
        normalizer_version=normalizer_version,
        provenance_classifier_version=semantic_classifier_version,
        provenance_ontology_version=provenance_ontology_version,
    )


def get_semantic_pending_rows(
    *,
    detector_version: str,
    metric_classifier_version: str,
    metric_ontology_version: str,
    normalizer_version: str,
    deterministic_classifier_version: str,
    provenance_ontology_version: str,
    semantic_classifier_version: str,
) -> list[dict]:
    return get_pending_semantic_provenance_input_rows(
        detector_version=detector_version,
        metric_classifier_version=metric_classifier_version,
        metric_ontology_version=metric_ontology_version,
        normalizer_version=normalizer_version,
        deterministic_classifier_version=deterministic_classifier_version,
        provenance_ontology_version=provenance_ontology_version,
        semantic_classifier_version=semantic_classifier_version,
    )


def update_semantic_provenance_cache(
    *,
    detector_version: str = DETECTOR_VERSION,
    metric_classifier_version: str = CLASSIFIER_VERSION,
    metric_ontology_version: str = ONTOLOGY_VERSION,
    normalizer_version: str = NORMALIZER_VERSION,
    deterministic_classifier_version: str = PROVENANCE_CLASSIFIER_VERSION,
    provenance_ontology_version: str = PROVENANCE_ONTOLOGY_VERSION,
    semantic_classifier_version: str = SEMANTIC_PROVENANCE_CLASSIFIER_VERSION,
    limit: int | None = None,
) -> dict:
    if limit is not None and limit <= 0:
        raise ValueError("limit must be greater than 0")

    _validate_active_versions(
        detector_version=detector_version,
        metric_classifier_version=metric_classifier_version,
        metric_ontology_version=metric_ontology_version,
        normalizer_version=normalizer_version,
        deterministic_classifier_version=deterministic_classifier_version,
        provenance_ontology_version=provenance_ontology_version,
        semantic_classifier_version=semantic_classifier_version,
    )

    cached_rows = get_semantic_cache_rows(
        detector_version=detector_version,
        metric_classifier_version=metric_classifier_version,
        metric_ontology_version=metric_ontology_version,
        normalizer_version=normalizer_version,
        semantic_classifier_version=semantic_classifier_version,
        provenance_ontology_version=provenance_ontology_version,
    )

    pending_rows = get_semantic_pending_rows(
        detector_version=detector_version,
        metric_classifier_version=metric_classifier_version,
        metric_ontology_version=metric_ontology_version,
        normalizer_version=normalizer_version,
        deterministic_classifier_version=deterministic_classifier_version,
        provenance_ontology_version=provenance_ontology_version,
        semantic_classifier_version=semantic_classifier_version,
    )

    total_target_count = len(cached_rows) + len(pending_rows)
    cached_count = len(cached_rows)

    selected_rows = (
        pending_rows
        if limit is None
        else pending_rows[:limit]
    )

    successful_now = 0
    failed_now = 0

    for index, row in enumerate(
        selected_rows,
        start=1,
    ):
        try:
            classification = classify_semantic_provenance(
                row
            )

            # Persist immediately so successful work survives a later
            # API failure or process interruption.
            upsert_provenance_classifications(
                [
                    classification.to_record()
                ]
            )

            successful_now += 1

        except Exception as error:
            failed_now += 1

            document_id = row.get(
                "document_id",
                "<unknown>",
            )
            page_number = row.get(
                "page_number",
                "<unknown>",
            )

            print(
                f"[{index}/{len(selected_rows)}] "
                "Semantic provenance failed: "
                f"document={document_id} "
                f"page={page_number} "
                f"{type(error).__name__}: {error}"
            )

    attempted_now = len(selected_rows)

    completed_count = (
        cached_count
        + successful_now
    )

    deferred_count = max(
        total_target_count
        - completed_count,
        0,
    )

    return {
        "detector_version":
            detector_version,

        "metric_classifier_version":
            metric_classifier_version,

        "metric_ontology_version":
            metric_ontology_version,

        "normalizer_version":
            normalizer_version,

        "deterministic_classifier_version":
            deterministic_classifier_version,

        "provenance_ontology_version":
            provenance_ontology_version,

        "semantic_classifier_version":
            semantic_classifier_version,

        "total_semantic_targets":
            total_target_count,

        "cached_semantic":
            cached_count,

        "attempted_now":
            attempted_now,

        "successful_now":
            successful_now,

        "failed_now":
            failed_now,

        "completed_semantic":
            completed_count,

        "deferred_semantic":
            deferred_count,

        "coverage_complete":
            (
                completed_count
                == total_target_count
            ),
    }


def print_statistics(
    *,
    detector_version: str = DETECTOR_VERSION,
    metric_classifier_version: str = CLASSIFIER_VERSION,
    metric_ontology_version: str = ONTOLOGY_VERSION,
    normalizer_version: str = NORMALIZER_VERSION,
    deterministic_classifier_version: str = PROVENANCE_CLASSIFIER_VERSION,
    provenance_ontology_version: str = PROVENANCE_ONTOLOGY_VERSION,
    semantic_classifier_version: str = SEMANTIC_PROVENANCE_CLASSIFIER_VERSION,
) -> None:
    cached_rows = get_semantic_cache_rows(
        detector_version=detector_version,
        metric_classifier_version=metric_classifier_version,
        metric_ontology_version=metric_ontology_version,
        normalizer_version=normalizer_version,
        semantic_classifier_version=semantic_classifier_version,
        provenance_ontology_version=provenance_ontology_version,
    )

    pending_rows = get_semantic_pending_rows(
        detector_version=detector_version,
        metric_classifier_version=metric_classifier_version,
        metric_ontology_version=metric_ontology_version,
        normalizer_version=normalizer_version,
        deterministic_classifier_version=deterministic_classifier_version,
        provenance_ontology_version=provenance_ontology_version,
        semantic_classifier_version=semantic_classifier_version,
    )

    total_target_count = (
        len(cached_rows)
        + len(pending_rows)
    )

    status_counts = Counter(
        row["status"]
        for row in cached_rows
    )

    provenance_counts = Counter(
        row["provenance"]
        for row in cached_rows
    )

    print()
    print("=" * 72)
    print("Semantic Provenance Statistics")
    print("=" * 72)
    print(
        "Semantic targets:",
        total_target_count,
    )
    print(
        "Cached semantic:",
        len(cached_rows),
    )
    print(
        "Pending semantic:",
        len(pending_rows),
    )

    coverage_ratio = (
        len(cached_rows)
        / total_target_count
        if total_target_count
        else 1.0
    )

    print(
        "Coverage:",
        f"{coverage_ratio:.1%}",
    )

    print()
    print("Semantic status")
    print("-" * 72)
    print(
        "Classified:",
        status_counts.get(
            "classified",
            0,
        ),
    )
    print(
        "Unresolved:",
        status_counts.get(
            "unresolved",
            0,
        ),
    )

    print()
    print("Semantic provenance")
    print("-" * 72)

    for key, count in (
        provenance_counts.most_common()
    ):
        print(
            f"{count:>6}  {key}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build the offline semantic provenance cache "
            "for deterministic provenance abstentions."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Maximum number of pending semantic LLM calls "
            "to attempt in this run."
        ),
    )

    parser.add_argument(
        "--stats-only",
        action="store_true",
    )

    args = parser.parse_args()

    if args.limit is not None and args.limit <= 0:
        parser.error(
            "--limit must be greater than 0"
        )

    init_db()

    if not args.stats_only:
        result = (
            update_semantic_provenance_cache(
                limit=args.limit
            )
        )

        print()
        print("=" * 72)
        print(
            "Semantic Provenance Update"
        )
        print("=" * 72)

        for key, value in (
            result.items()
        ):
            print(
                f"{key}: {value}"
            )

    print_statistics()


if __name__ == "__main__":
    main()
