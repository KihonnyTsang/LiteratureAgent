import re
from dataclasses import dataclass


PROVENANCE_ONTOLOGY_VERSION = (
    "provenance-ontology-v4"
)


@dataclass(frozen=True)
class ProvenanceRule:
    pattern: str
    weight: int
    context_safe: bool = True


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

            # Strong first-person current-work evidence.
            ProvenanceRule(
                pattern=(
                    r"\bwe\s+"
                    r"(?:(?:have|had)\s+)?"
                    r"(?:"
                    r"measured|measure|"
                    r"obtained|obtain|"
                    r"achieved|"
                    r"demonstrated|demonstrate|"
                    r"calculated|calculate|"
                    r"observed|observe|"
                    r"found|find|"
                    r"fabricated|fabricate|"
                    r"developed|develop|"
                    r"prepared|prepare|"
                    r"reported|report|"
                    r"presented|present|"
                    r"show|shows"
                    r")\b"
                ),
                weight=4,
            ),

            ProvenanceRule(
                pattern=(
                    r"\bwe\s+achieve\b"
                ),
                weight=4,
                context_safe=False,
            ),

            # Strong possessive current-work evidence.
            ProvenanceRule(
                pattern=(
                    r"\bour\s+"
                    r"(?:"
                    r"device|devices|"
                    r"generator|generators|"
                    r"prototype|prototypes|"
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

            # "our work/study" is explicit ownership.
            ProvenanceRule(
                pattern=(
                    r"\b(?:in|from)\s+"
                    r"our\s+"
                    r"(?:work|study)\b"
                ),
                weight=3,
            ),

            # "the present work/study" refers to the current
            # paper much more reliably than "this work/study",
            # which is common inside literature-review prose.
            ProvenanceRule(
                pattern=(
                    r"\b(?:in|from)\s+"
                    r"(?:the\s+)?present\s+"
                    r"(?:work|study)\b"
                ),
                weight=3,
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
                    r"\bet\s+al\.?\s*"
                    r"(?:"
                    r"\[\s*\d+(?:\s*[-,]\s*\d+)*\s*\]"
                    r"|"
                    r"\d+"
                    r")?"
                    r"\s*"
                    r"(?:"
                    r"reported|reports|"
                    r"demonstrated|demonstrates|"
                    r"achieved|achieves|"
                    r"obtained|obtains|"
                    r"showed|shows|"
                    r"investigated|investigate|investigates|"
                    r"proposed|propose|proposes|"
                    r"developed|develop|develops|"
                    r"described|describe|describes|"
                    r"presented|present|presents|"
                    r"measured|measure|measures|"
                    r"found|find|finds"
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
    *,
    context_safe_only: bool = False,
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

            if (
                context_safe_only
                and
                not rule.context_safe
            ):

                continue

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