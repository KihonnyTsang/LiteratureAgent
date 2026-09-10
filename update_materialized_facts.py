import argparse

from app.enrichment.fact_materializer import (
    FACT_MATERIALIZER_SCOPE,
    FACT_MATERIALIZER_VERSION,
    get_materialized_fact_rows,
    materialize_structured_facts,
)


def print_current_statistics() -> None:

    rows = (
        get_materialized_fact_rows()
    )

    author_result = sum(
        1
        for row
        in rows
        if row[
            "provenance"
        ]
        == "author_result"
    )

    cited_literature = sum(
        1
        for row
        in rows
        if row[
            "provenance"
        ]
        == "cited_literature"
    )

    uncertain = sum(
        1
        for row
        in rows
        if row[
            "provenance"
        ]
        == "uncertain"
    )

    normalization_errors = sum(
        1
        for row
        in rows
        if row[
            "normalization_error"
        ]
    )

    print()
    print("=" * 72)
    print(
        "Structured Fact Statistics"
    )
    print("=" * 72)
    print(
        "materializer_version:",
        FACT_MATERIALIZER_VERSION,
    )
    print(
        "materializer_scope:",
        FACT_MATERIALIZER_SCOPE,
    )
    print(
        "facts:",
        len(rows),
    )
    print(
        "author_result:",
        author_result,
    )
    print(
        "cited_literature:",
        cited_literature,
    )
    print(
        "uncertain:",
        uncertain,
    )
    print(
        "normalization_errors:",
        normalization_errors,
    )


def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Materialize metric-classified numeric "
            "mentions into the SQLite facts cache."
        )
    )

    parser.add_argument(
        "--stats-only",
        action="store_true",
    )

    args = parser.parse_args()

    if not args.stats_only:

        result = (
            materialize_structured_facts()
        )

        print()
        print("=" * 72)
        print(
            "Structured Fact Materialization"
        )
        print("=" * 72)

        for key, value in (
            result.items()
        ):
            if key == "metric_counts":
                continue

            print(
                f"{key}: {value}"
            )

        print()
        print("Metrics")
        print("-" * 72)

        for (
            metric_key,
            count,
        ) in result[
            "metric_counts"
        ].items():

            print(
                f"{count:>6}  "
                f"{metric_key}"
            )

    print_current_statistics()


if __name__ == "__main__":
    main()
