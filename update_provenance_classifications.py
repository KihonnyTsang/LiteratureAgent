import argparse
from collections import Counter

from app.database.sqlite_db import (
    init_db,
)

from app.database.enrichment_repository import (
    get_pending_provenance_input_rows,
    get_provenance_classification_rows,
    upsert_provenance_classifications,
)

from app.enrichment.metric_classifier import (
    CLASSIFIER_VERSION,
)

from app.enrichment.metric_ontology import (
    ONTOLOGY_VERSION,
)

from app.enrichment.numeric_scanner import (
    DETECTOR_VERSION,
)

from app.enrichment.provenance_classifier import (
    PROVENANCE_CLASSIFIER_VERSION,
    classify_provenance,
)

from app.enrichment.provenance_ontology import (
    PROVENANCE_ONTOLOGY_VERSION,
)

from app.enrichment.unit_signature import (
    NORMALIZER_VERSION,
)


def update_provenance_cache(
    *,
    detector_version: str,
    metric_classifier_version: str,
    ontology_version: str,
    normalizer_version: str,
    provenance_classifier_version: str,
    provenance_ontology_version: str,
    limit: int | None,
) -> dict:

    if (
        metric_classifier_version
        != CLASSIFIER_VERSION
    ):

        raise ValueError(
            "metric classifier version "
            "does not match active implementation"
        )

    if (
        ontology_version
        != ONTOLOGY_VERSION
    ):

        raise ValueError(
            "metric ontology version "
            "does not match active implementation"
        )

    if (
        normalizer_version
        != NORMALIZER_VERSION
    ):

        raise ValueError(
            "normalizer version "
            "does not match active implementation"
        )

    if (
        provenance_classifier_version
        != PROVENANCE_CLASSIFIER_VERSION
    ):

        raise ValueError(
            "provenance classifier version "
            "does not match active implementation"
        )

    if (
        provenance_ontology_version
        != PROVENANCE_ONTOLOGY_VERSION
    ):

        raise ValueError(
            "provenance ontology version "
            "does not match active implementation"
        )

    existing_rows = (
        get_provenance_classification_rows(
            detector_version=(
                detector_version
            ),

            metric_classifier_version=(
                metric_classifier_version
            ),

            ontology_version=(
                ontology_version
            ),

            normalizer_version=(
                normalizer_version
            ),

            provenance_classifier_version=(
                provenance_classifier_version
            ),

            provenance_ontology_version=(
                provenance_ontology_version
            ),
        )
    )

    pending_rows = (
        get_pending_provenance_input_rows(
            detector_version=(
                detector_version
            ),

            metric_classifier_version=(
                metric_classifier_version
            ),

            ontology_version=(
                ontology_version
            ),

            normalizer_version=(
                normalizer_version
            ),

            provenance_classifier_version=(
                provenance_classifier_version
            ),

            provenance_ontology_version=(
                provenance_ontology_version
            ),
        )
    )

    total_count = (
        len(existing_rows)
        + len(pending_rows)
    )

    cached_count = len(
        existing_rows
    )

    if limit is not None:

        pending_rows = (
            pending_rows[
                :limit
            ]
        )

    records = [
        classify_provenance(
            row
        ).to_record()

        for row
        in pending_rows
    ]

    upsert_provenance_classifications(
        records
    )

    completed_count = (
        cached_count
        + len(records)
    )

    return {
        "detector_version":
            detector_version,

        "metric_classifier_version":
            metric_classifier_version,

        "metric_ontology_version":
            ontology_version,

        "normalizer_version":
            normalizer_version,

        "provenance_classifier_version":
            provenance_classifier_version,

        "provenance_ontology_version":
            provenance_ontology_version,

        "total_metric_classified_mentions":
            total_count,

        "cached_provenance":
            cached_count,

        "processed_now":
            len(records),

        "completed_provenance":
            completed_count,

        "deferred_provenance":
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
    metric_classifier_version: str,
    ontology_version: str,
    normalizer_version: str,
    provenance_classifier_version: str,
    provenance_ontology_version: str,
) -> None:

    rows = (
        get_provenance_classification_rows(
            detector_version=(
                detector_version
            ),

            metric_classifier_version=(
                metric_classifier_version
            ),

            ontology_version=(
                ontology_version
            ),

            normalizer_version=(
                normalizer_version
            ),

            provenance_classifier_version=(
                provenance_classifier_version
            ),

            provenance_ontology_version=(
                provenance_ontology_version
            ),
        )
    )

    status_counts = Counter(
        row["status"]
        for row in rows
    )

    provenance_counts = Counter(
        row["provenance"]
        for row in rows
    )

    reason_counts = Counter(
        row["reason"]
        for row in rows
    )

    print()
    print("=" * 72)
    print(
        "Provenance Classification Statistics"
    )
    print("=" * 72)

    print(
        "Cached provenance:",
        len(rows),
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

    print()
    print("Provenance")
    print("-" * 72)

    for key, count in (
        provenance_counts.most_common()
    ):

        print(
            f"{count:>6}  {key}"
        )

    print()
    print("Reasons")
    print("-" * 72)

    for key, count in (
        reason_counts.most_common()
    ):

        print(
            f"{count:>6}  {key}"
        )


def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Build deterministic provenance "
            "classification cache."
        )
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

        result = update_provenance_cache(
            detector_version=(
                DETECTOR_VERSION
            ),

            metric_classifier_version=(
                CLASSIFIER_VERSION
            ),

            ontology_version=(
                ONTOLOGY_VERSION
            ),

            normalizer_version=(
                NORMALIZER_VERSION
            ),

            provenance_classifier_version=(
                PROVENANCE_CLASSIFIER_VERSION
            ),

            provenance_ontology_version=(
                PROVENANCE_ONTOLOGY_VERSION
            ),

            limit=args.limit,
        )

        print()
        print("=" * 72)
        print(
            "Provenance Classification Update"
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
            DETECTOR_VERSION
        ),

        metric_classifier_version=(
            CLASSIFIER_VERSION
        ),

        ontology_version=(
            ONTOLOGY_VERSION
        ),

        normalizer_version=(
            NORMALIZER_VERSION
        ),

        provenance_classifier_version=(
            PROVENANCE_CLASSIFIER_VERSION
        ),

        provenance_ontology_version=(
            PROVENANCE_ONTOLOGY_VERSION
        ),
    )


if __name__ == "__main__":

    main()