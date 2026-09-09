import re
from dataclasses import dataclass


PROVENANCE_ONTOLOGY_VERSION = (
    "provenance-ontology-v2"
)


@dataclass(frozen=True)
class ProvenanceRule:
    pattern: str
    weight: int


@dataclass(frozen=True)
class ProvenanceSpec:
    key: str
    rules: tuple[
        ProvenanceRule,
        ...,
    ]


# ============================================================
# Generic scientific provenance ontology
#
# 注意：
#
# 这里描述的是论文写作中的来源语义。
#
# 不包含：
# - metric 名称
# - PENG / TENG
# - 作者名字
# - 固定论文
# - 固定数值
#
# classifier 只消费这些规则，
# 不写 provenance-specific if/elif。
# ============================================================

PROVENANCE_ONTOLOGY = {

    "author_result": ProvenanceSpec(
        key="author_result",

        rules=(

            ProvenanceRule(
                pattern=(
                    r"\bwe\s+"
                    r"(?:(?:have|had)\s+)?"
                    r"(?:"
                    r"measured|measure|"
                    r"obtained|obtain|"
                    r"achieved|achieve|"
                    r"demonstrated|demonstrate|"
                    r"calculated|calculate|"
                    r"observed|observe|"
                    r"found|find|"
                    r"fabricated|fabricate|"
                    r"developed|develop|"
                    r"prepared|prepare|"
                    r"reported|report|"
                    r"show|shows"
                    r")\b"
                ),
                weight=4,
            ),

            ProvenanceRule(
                pattern=(
                    r"\bour\s+"
                    r"(?:"
                    r"device|devices|"
                    r"generator|generators|"
                    r"sample|samples|"
                    r"film|films|"
                    r"system|systems|"
                    r"sensor|sensors|"
                    r"result|results|"
                    r"measurement|measurements"
                    r")\b"
                ),
                weight=3,
            ),

            ProvenanceRule(
                pattern=(
                    r"\b(?:in|from)\s+"
                    r"this\s+"
                    r"(?:work|study)\b"
                ),
                weight=3,
            ),

            ProvenanceRule(
                pattern=(
                    r"\bthis\s+"
                    r"(?:work|study)\s+"
                    r"(?:"
                    r"reports?|"
                    r"demonstrates?|"
                    r"shows?|"
                    r"presents?|"
                    r"achieves?|"
                    r"obtains?"
                    r")\b"
                ),
                weight=4,
            ),
        ),
    ),

    "cited_literature": ProvenanceSpec(
        key="cited_literature",

        rules=(

            ProvenanceRule(
                pattern=(
                    r"\bpreviously\s+reported\b"
                ),
                weight=2,
            ),

            ProvenanceRule(
                pattern=(
                    r"\bprevious\s+"
                    r"(?:"
                    r"work|study|studies|literature"
                    r")\b"
                ),
                weight=3,
            ),

            ProvenanceRule(
                pattern=(
                    r"\bprior\s+"
                    r"(?:"
                    r"work|study|studies|literature"
                    r")\b"
                ),
                weight=3,
            ),

            ProvenanceRule(
                pattern=(
                    r"\breported\s+by\b"
                ),
                weight=4,
            ),

            ProvenanceRule(
                pattern=(
                    r"\bet\s+al\.?\s+"
                    r"(?:"
                    r"reported|"
                    r"demonstrated|"
                    r"achieved|"
                    r"obtained|"
                    r"showed"
                    r")\b"
                ),
                weight=4,
            ),

            ProvenanceRule(
                pattern=(
                    r"\breported\s+in\s+"
                    r"(?:the\s+)?literature\b"
                ),
                weight=4,
            ),

            ProvenanceRule(
                pattern=(
                    r"\b(?:"
                    r"literature|"
                    r"studies|"
                    r"reports"
                    r")\s+"
                    r"(?:"
                    r"reported|"
                    r"shows?|"
                    r"showed|"
                    r"demonstrated"
                    r")\b"
                ),
                weight=3,
            ),
        ),
    ),
}


def normalize_provenance_text(
    text: str,
) -> str:
    """
    Normalize PDF extraction artifacts
    for provenance lexical routing.

    原始 evidence 不会被修改。
    """

    normalized = text.lower()

    normalized = (
        normalized
        .replace(
            "−",
            "-",
        )
        .replace(
            "–",
            "-",
        )
        .replace(
            "—",
            "-",
        )
    )

    # PDF word wrapping:
    #
    # previous-
    # ly
    #
    # -> previously
    normalized = re.sub(
        r"""
        (?<=\w)
        -
        \s+
        (?=\w)
        """,
        "",
        normalized,
        flags=re.VERBOSE,
    )

    normalized = (
        normalized.replace(
            "-",
            " ",
        )
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    ).strip()

    return normalized


def rank_provenance_candidates(
    text: str,
) -> list[
    tuple[str, int]
]:
    """
    Generic ontology-driven provenance scoring.
    """

    normalized_text = (
        normalize_provenance_text(
            text
        )
    )

    ranked = []

    for (
        provenance_key,
        spec,
    ) in PROVENANCE_ONTOLOGY.items():

        score = 0

        for rule in spec.rules:

            if re.search(
                rule.pattern,
                normalized_text,
            ):

                score += (
                    rule.weight
                )

        ranked.append(
            (
                provenance_key,
                score,
            )
        )

    return sorted(
        ranked,
        key=lambda item: (
            -item[1],
            item[0],
        ),
    )