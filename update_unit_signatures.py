import argparse
from collections import Counter

from app.database.sqlite_db import (
    init_db,
)

from app.database.enrichment_repository import (
    get_current_unit_signature_units,
    get_distinct_numeric_units,
    get_unit_signature_rows,
    upsert_unit_signatures,
)

from app.enrichment.numeric_scanner import (
    DETECTOR_VERSION,
)

from app.enrichment.unit_signature import (
    NORMALIZER_VERSION,
    build_unit_signature,
)


def update_unit_signature_cache(
    *,
    detector_version: str,
    normalizer_version: str,
) -> dict:

    raw_units = (
        get_distinct_numeric_units(
            detector_version=(
                detector_version
            )
        )
    )

    cached_units = (
        get_current_unit_signature_units(
            normalizer_version=(
                normalizer_version
            )
        )
    )

    pending_units = [
        raw_unit
        for raw_unit
        in raw_units
        if raw_unit
        not in cached_units
    ]

    signatures = []

    for raw_unit in pending_units:

        signature = (
            build_unit_signature(
                raw_unit,
                normalizer_version=(
                    normalizer_version
                ),
            )
        )

        signatures.append(
            signature.to_record()
        )

    upsert_unit_signatures(
        signatures
    )

    current_raw_unit_set = set(
        raw_units
    )

    cached_current_units = (
            current_raw_unit_set
            & cached_units
    )

    stale_cached_units = (
            cached_units
            - current_raw_unit_set
    )

    return {
        "detector_version":
            detector_version,

        "normalizer_version":
            normalizer_version,

        "raw_unit_count":
            len(
                current_raw_unit_set
            ),

        "cached_unit_count":
            len(
                cached_current_units
            ),

        "processed_unit_count":
            len(
                signatures
            ),

        "stale_cached_unit_count":
            len(
                stale_cached_units
            ),
    }


def print_statistics(
    *,
    detector_version: str,
    normalizer_version: str,
    top_dimensions: int,
    invalid_examples: int,
) -> None:

    rows = get_unit_signature_rows(
        normalizer_version=(
            normalizer_version
        )
    )

    current_raw_units = set(
        get_distinct_numeric_units(
            detector_version=(
                detector_version
            )
        )
    )

    rows = [
        row
        for row in rows
        if row["raw_unit"]
        in current_raw_units
    ]

    status_counts = Counter(
        row["parse_status"]
        for row in rows
    )

    dimension_counts = Counter(
        row["dimensionality"]
        for row in rows
        if row[
            "dimensionality"
        ]
    )

    invalid_rows = [
        row
        for row in rows
        if row[
            "parse_status"
        ]
        == "invalid"
    ]

    print()
    print("=" * 72)
    print("Unit Signature Statistics")
    print("=" * 72)

    print(
        "Normalizer version:",
        normalizer_version,
    )

    print(
        "Unit signatures:",
        len(rows),
    )

    print(
        "Valid:",
        status_counts.get(
            "valid",
            0,
        ),
    )

    print(
        "Custom:",
        status_counts.get(
            "custom",
            0,
        ),
    )

    print(
        "Invalid:",
        status_counts.get(
            "invalid",
            0,
        ),
    )

    print()
    print(
        f"Top {top_dimensions} "
        "dimensionalities"
    )
    print("-" * 72)

    for (
        dimensionality,
        count,
    ) in dimension_counts.most_common(
        top_dimensions
    ):

        print(
            f"{count:>6}  "
            f"{dimensionality}"
        )

    print()
    print(
        f"First {invalid_examples} "
        "invalid raw units"
    )
    print("-" * 72)

    for row in (
        invalid_rows[
            :invalid_examples
        ]
    ):

        print(
            row[
                "raw_unit"
            ],
            "->",
            row[
                "normalized_unit_text"
            ],
        )


def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Build deterministic unit "
            "signatures for numeric mentions."
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
        "--top-dimensions",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--invalid-examples",
        type=int,
        default=40,
    )

    parser.add_argument(
        "--stats-only",
        action="store_true",
    )

    args = parser.parse_args()

    init_db()

    if not args.stats_only:

        result = (
            update_unit_signature_cache(
                detector_version=(
                    args.detector_version
                ),

                normalizer_version=(
                    args.normalizer_version
                ),
            )
        )

        print()
        print("=" * 72)
        print("Unit Signature Update")
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

        normalizer_version=(
            args.normalizer_version
        ),

        top_dimensions=(
            args.top_dimensions
        ),

        invalid_examples=(
            args.invalid_examples
        ),
    )


if __name__ == "__main__":

    main()