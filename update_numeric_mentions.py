import argparse

from app.database.sqlite_db import (
    get_connection,
    init_db,
)

from app.enrichment.numeric_scanner import (
    DETECTOR_VERSION,
    update_numeric_mentions,
)


def print_numeric_statistics(
    *,
    detector_version: str,
    top_units: int,
) -> None:
    """
    打印当前 Numeric Mention Cache 的统计信息。
    """

    connection = get_connection()

    try:

        total_documents = (
            connection.execute(
                """
                SELECT COUNT(*)
                FROM documents
                """
            )
            .fetchone()[0]
        )

        scanned_documents = (
            connection.execute(
                """
                SELECT COUNT(*)

                FROM numeric_scan_runs

                WHERE detector_version = ?
                  AND status = 'success'
                """,
                (
                    detector_version,
                ),
            )
            .fetchone()[0]
        )

        total_mentions = (
            connection.execute(
                """
                SELECT COUNT(*)

                FROM numeric_mentions

                WHERE detector_version = ?
                """,
                (
                    detector_version,
                ),
            )
            .fetchone()[0]
        )

        unique_units = (
            connection.execute(
                """
                SELECT COUNT(
                    DISTINCT raw_unit
                )

                FROM numeric_mentions

                WHERE detector_version = ?
                  AND raw_unit IS NOT NULL
                """,
                (
                    detector_version,
                ),
            )
            .fetchone()[0]
        )

        zero_mention_documents = (
            connection.execute(
                """
                SELECT COUNT(*)

                FROM numeric_scan_runs

                WHERE detector_version = ?
                  AND status = 'success'
                  AND mention_count = 0
                """,
                (
                    detector_version,
                ),
            )
            .fetchone()[0]
        )

        top_unit_rows = (
            connection.execute(
                """
                SELECT
                    raw_unit,
                    COUNT(*) AS mention_count

                FROM numeric_mentions

                WHERE detector_version = ?
                  AND raw_unit IS NOT NULL

                GROUP BY raw_unit

                ORDER BY
                    mention_count DESC,
                    raw_unit

                LIMIT ?
                """,
                (
                    detector_version,
                    top_units,
                ),
            )
            .fetchall()
        )

    finally:

        connection.close()

    print()
    print("=" * 72)
    print("Numeric Mention Statistics")
    print("=" * 72)

    print(
        "Detector version:",
        detector_version,
    )

    print(
        "Documents:",
        total_documents,
    )

    print(
        "Scanned documents:",
        scanned_documents,
    )

    print(
        "Zero-mention documents:",
        zero_mention_documents,
    )

    print(
        "Numeric mentions:",
        total_mentions,
    )

    print(
        "Unique raw units:",
        unique_units,
    )

    if total_documents:

        coverage_ratio = (
            scanned_documents
            / total_documents
        )

    else:

        coverage_ratio = 1.0

    print(
        "Coverage:",
        f"{coverage_ratio:.1%}",
    )

    print()
    print(
        f"Top {top_units} units"
    )
    print("-" * 72)

    for (
        raw_unit,
        mention_count,
    ) in top_unit_rows:

        print(
            f"{mention_count:>8}  "
            f"{raw_unit}"
        )


def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Incrementally scan the literature "
            "database for numeric mentions."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Maximum number of currently "
            "unscanned documents to process."
        ),
    )

    parser.add_argument(
        "--detector-version",
        default=DETECTOR_VERSION,
        help=(
            "Numeric scanner version."
        ),
    )

    parser.add_argument(
        "--top-units",
        type=int,
        default=30,
        help=(
            "Number of most frequent raw units "
            "to display."
        ),
    )

    parser.add_argument(
        "--stats-only",
        action="store_true",
        help=(
            "Do not scan documents; "
            "only show current statistics."
        ),
    )

    args = parser.parse_args()

    init_db()

    if not args.stats_only:

        result = (
            update_numeric_mentions(
                detector_version=(
                    args.detector_version
                ),
                limit=args.limit,
            )
        )

        print()
        print("=" * 72)
        print("Numeric Scan Result")
        print("=" * 72)

        for key, value in (
            result.items()
        ):

            print(
                f"{key}: {value}"
            )

    print_numeric_statistics(
        detector_version=(
            args.detector_version
        ),
        top_units=args.top_units,
    )


if __name__ == "__main__":

    main()