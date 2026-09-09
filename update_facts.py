import argparse
from pprint import pprint

from app.tools.fact_tool import (
    update_fact_cache,
)


def parse_args(
) -> argparse.Namespace:
    """
    解析离线 Fact Extraction 参数。
    """

    parser = argparse.ArgumentParser(
        description=(
            "Incrementally build "
            "LiteratureAgent structured "
            "fact cache."
        )
    )

    parser.add_argument(
        "--metric",
        required=True,
        help=(
            "Metric key or supported "
            "metric name."
        ),
    )

    parser.add_argument(
        "--scope",
        default="all_documents",
        help=(
            "Document selection scope. "
            "Default: all_documents."
        ),
    )

    parser.add_argument(
        "--provenance-scope",
        default="author_results",
        choices=[
            "author_results",
            "all_mentions",
        ],
        help=(
            "Fact provenance scope."
        ),
    )

    parser.add_argument(
        "--document-name",
        action="append",
        dest="document_names",
        help=(
            "Optional document name. "
            "Can be provided multiple times."
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "Maximum number of cache-miss "
            "documents to extract in this run."
        ),
    )

    return parser.parse_args()


def main(
) -> None:

    args = parse_args()

    print()
    print("=" * 72)
    print(
        "LiteratureAgent - "
        "Structured Fact Update"
    )
    print("=" * 72)

    result = update_fact_cache(
        metric=args.metric,
        scope=args.scope,
        provenance_scope=(
            args.provenance_scope
        ),
        document_names=(
            args.document_names
        ),
        limit=args.limit,
    )

    print()
    print("=" * 72)
    print("Fact Update Summary")
    print("=" * 72)

    pprint(
        result,
        sort_dicts=False,
    )

    print("=" * 72)


if __name__ == "__main__":
    main()