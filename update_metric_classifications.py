import argparse
from collections import Counter

from app.database.sqlite_db import (
    init_db,
)

from app.database.enrichment_repository import (
    get_current_metric_classification_mention_ids,
    get_metric_classification_rows,
    get_numeric_mentions,
    upsert_metric_classifications,
)

from app.enrichment.metric_classifier import (
    CLASSIFIER_VERSION,
    classify_numeric_mention,
)

from app.enrichment.metric_ontology import (
    ONTOLOGY_VERSION,
)

from app.enrichment.numeric_scanner import (
    DETECTOR_VERSION,
)

from app.enrichment.unit_signature import (
    NORMALIZER_VERSION,
)


def update_metric_classification_cache(
    *,
    detector_version: str,
    classifier_version: str,
    ontology_version: str,
    normalizer_version: str,
    limit: int | None,
) -> dict:

    if (
        classifier_version
        != CLASSIFIER_VERSION
    ):

        raise ValueError(
            "classifier_version does not "
            "match the active implementation: "
            f"{classifier_version!r} != "
            f"{CLASSIFIER_VERSION!r}"
        )

    if (
        ontology_version
        != ONTOLOGY_VERSION
    ):

        raise ValueError(
            "ontology_version does not "
            "match the active implementation: "
            f"{ontology_version!r} != "
            f"{ONTOLOGY_VERSION!r}"
        )

    if (
        normalizer_version
        != NORMALIZER_VERSION
    ):

        raise ValueError(
            "normalizer_version does not "
            "match the active implementation: "
            f"{normalizer_version!r} != "
            f"{NORMALIZER_VERSION!r}"
        )

    mentions = get_numeric_mentions(
        detector_version=(
            detector_version
        )
    )

    cached_ids = (
        get_current_metric_classification_mention_ids(
            detector_version=(
                detector_version
            ),

            classifier_version=(
                classifier_version
            ),

            ontology_version=(
                ontology_version
            ),

            normalizer_version=(
                normalizer_version
            ),
        )
    )

    pending_mentions = [
        mention
        for mention in mentions
        if int(
            mention["id"]
        )
        not in cached_ids
    ]

    if limit is not None:

        pending_mentions = (
            pending_mentions[
                :limit
            ]
        )

    records = [
        classify_numeric_mention(
            mention
        ).to_record()

        for mention
        in pending_mentions
    ]

    upsert_metric_classifications(
        records
    )

    completed_count = (
        len(cached_ids)
        + len(records)
    )

    total_count = len(
        mentions
    )

    return {
        "detector_version":
            detector_version,

        "normalizer_version":
            normalizer_version,

        "ontology_version":
            ontology_version,

        "classifier_version":
            classifier_version,

        "total_mentions":
            total_count,

        "cached_mentions":
            len(cached_ids),

        "processed_now":
            len(records),

        "completed_mentions":
            completed_count,

        "deferred_mentions":
            max(
                total_count
                - completed_count,
                0,
            ),

        "coverage_complete":
            (
                completed_count
                == total_count
            ),
    }


def print_statistics(
    *,
    detector_version: str,
    classifier_version: str,
    ontology_version: str,
    normalizer_version: str,
) -> None:

    mentions = get_numeric_mentions(
        detector_version=(
            detector_version
        )
    )

    rows = (
        get_metric_classification_rows(
            detector_version=(
                detector_version
            ),

            classifier_version=(
                classifier_version
            ),

            ontology_version=(
                ontology_version
            ),

            normalizer_version=(
                normalizer_version
            ),
        )
    )

    status_counts = Counter(
        row["status"]
        for row in rows
    )

    metric_counts = Counter(
        row["metric_key"]
        for row in rows
        if (
            row["status"]
            == "classified"
            and
            row["metric_key"]
            is not None
        )
    )

    reason_counts = Counter(
        row["reason"]
        for row in rows
    )

    total_mentions = len(
        mentions
    )

    cached_mentions = len(
        rows
    )

    coverage = (
        cached_mentions
        / total_mentions
        if total_mentions
        else 1.0
    )

    print()
    print("=" * 72)
    print(
        "Metric Classification Statistics"
    )
    print("=" * 72)

    print(
        "Detector version:",
        detector_version,
    )

    print(
        "Normalizer version:",
        normalizer_version,
    )

    print(
        "Ontology version:",
        ontology_version,
    )

    print(
        "Classifier version:",
        classifier_version,
    )

    print(
        "Numeric mentions:",
        total_mentions,
    )

    print(
        "Cached classifications:",
        cached_mentions,
    )

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

    print(
        "Rejected:",
        status_counts.get(
            "rejected",
            0,
        ),
    )

    print(
        "Coverage:",
        f"{coverage:.1%}",
    )

    print()
    print(
        "Top classified metrics"
    )
    print("-" * 72)

    for (
        metric_key,
        count,
    ) in metric_counts.most_common(
        30
    ):

        print(
            f"{count:>6}  "
            f"{metric_key}"
        )

    print()
    print(
        "Classification reasons"
    )
    print("-" * 72)

    for (
        reason,
        count,
    ) in reason_counts.most_common():

        print(
            f"{count:>6}  "
            f"{reason}"
        )


def main() -> None:

    parser = (
        argparse.ArgumentParser(
            description=(
                "Build deterministic "
                "metric classification cache "
                "for Numeric Mentions."
            )
        )
    )

    parser.add_argument(
        "--detector-version",
        default=DETECTOR_VERSION,
    )

    parser.add_argument(
        "--normalizer-version",
        default=NORMALIZER_VERSION,
    )

    parser.add_argument(
        "--ontology-version",
        default=ONTOLOGY_VERSION,
    )

    parser.add_argument(
        "--classifier-version",
        default=CLASSIFIER_VERSION,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--stats-only",
        action="store_true",
    )

    args = parser.parse_args()

    if (
        args.limit is not None
        and args.limit <= 0
    ):

        parser.error(
            "--limit must be > 0"
        )

    init_db()

    if not args.stats_only:

        result = (
            update_metric_classification_cache(
                detector_version=(
                    args.detector_version
                ),

                classifier_version=(
                    args.classifier_version
                ),

                ontology_version=(
                    args.ontology_version
                ),

                normalizer_version=(
                    args.normalizer_version
                ),

                limit=args.limit,
            )
        )

        print()
        print("=" * 72)
        print(
            "Metric Classification Update"
        )
        print("=" * 72)

        for key, value in (
            result.items()
        ):

            print(
                f"{key}: {value}"
            )

    print_statistics(
        detector_version=(
            args.detector_version
        ),

        classifier_version=(
            args.classifier_version
        ),

        ontology_version=(
            args.ontology_version
        ),

        normalizer_version=(
            args.normalizer_version
        ),
    )


if __name__ == "__main__":

    main()