import re
from dataclasses import dataclass
from typing import Iterable

from app.database.sqlite_db import (
    get_connection,
)

from app.database.enrichment_repository import (
    has_current_numeric_scan,
    replace_numeric_scan_result,
)


DETECTOR_VERSION = "numeric-v2"


# ============================================================
# PDF extraction control characters
#
# Some PDFs contain invisible C0 control characters inside
# otherwise valid scientific units, for example:
#
#     cm\x032
#
# visually rendered as:
#
#     cm2
#
# These characters are extraction artifacts rather than
# semantic delimiters.
# ============================================================


# ============================================================
# Numeric grammar
# ============================================================

NUMBER_PATTERN = r"""
[+-]?
(?:
    (?:\d{1,3}(?:,\d{3})+)
    |
    (?:\d+(?:\.\d+)?)
    |
    (?:\.\d+)
)
(?:[eE][+-]?\d+)?
"""


# ============================================================
# Unit lexicon
#
# v1 只扫描“显式带单位”的数字。
#
# 这样可以避免：
#
# 2018
# Figure 3
# sample 5
# reference [12]
#
# 等大量非科研量值污染。
#
# 这属于稳定的 scientific unit contract，
# 不是 metric/question-specific hardcoding。
# ============================================================

UNIT_BASES = [
    # --------------------------------------------------------
    # Percentage / composition
    # --------------------------------------------------------
    # 带空格和不带空格的 composition 写法都保留。
    #
    # PDF extraction 中常见：
    #
    # 10 wt%
    # 10 wt %
    #
    "wt %",
    "mol %",
    "vol %",
    "at %",

    "wt%",
    "mol%",
    "vol%",
    "at%",

    "%",

    # --------------------------------------------------------
    # Temperature
    # --------------------------------------------------------
    "°C",
    "℃",
    "K",

    # --------------------------------------------------------
    # Voltage
    # --------------------------------------------------------
    "μV",
    "uV",
    "mV",
    "kV",
    "MV",
    "V",

    # --------------------------------------------------------
    # Current
    # --------------------------------------------------------
    "pA",
    "nA",
    "μA",
    "uA",
    "mA",
    "kA",
    "A",

    # --------------------------------------------------------
    # Power
    # --------------------------------------------------------
    "pW",
    "nW",
    "μW",
    "uW",
    "mW",
    "kW",
    "MW",
    "W",

    # --------------------------------------------------------
    # Energy
    # --------------------------------------------------------
    "μJ",
    "uJ",
    "mJ",
    "kJ",
    "MJ",
    "J",
    "meV",
    "keV",
    "eV",

    # --------------------------------------------------------
    # Charge
    # --------------------------------------------------------
    "pC",
    "nC",
    "μC",
    "uC",
    "mC",
    "C",

    # --------------------------------------------------------
    # Force
    # --------------------------------------------------------
    "μN",
    "uN",
    "mN",
    "kN",
    "N",

    # --------------------------------------------------------
    # Pressure / modulus
    # --------------------------------------------------------
    "Pa",
    "kPa",
    "MPa",
    "GPa",
    "TPa",

    # --------------------------------------------------------
    # Frequency
    # --------------------------------------------------------
    "mHz",
    "Hz",
    "kHz",
    "MHz",
    "GHz",

    # --------------------------------------------------------
    # Length
    # --------------------------------------------------------
    "pm",
    "nm",
    "μm",
    "um",
    "mm",
    "cm",
    "km",
    "m",

    # --------------------------------------------------------
    # Time
    # --------------------------------------------------------
    "ns",
    "μs",
    "us",
    "ms",
    "min",
    "h",
    "s",

    # --------------------------------------------------------
    # Mass
    # --------------------------------------------------------
    "μg",
    "ug",
    "mg",
    "kg",
    "g",

    # --------------------------------------------------------
    # Capacitance
    # --------------------------------------------------------
    "pF",
    "nF",
    "μF",
    "uF",
    "mF",
    "F",

    # --------------------------------------------------------
    # Resistance
    # --------------------------------------------------------
    "mΩ",
    "kΩ",
    "MΩ",
    "GΩ",
    "Ω",
    "ohm",

    # --------------------------------------------------------
    # Conductance
    # --------------------------------------------------------
    "μS",
    "uS",
    "mS",
    "S",

    # --------------------------------------------------------
    # Magnetic
    # --------------------------------------------------------
    "mT",
    "T",
    "Oe",

    # --------------------------------------------------------
    # Rotation
    # --------------------------------------------------------
    "rpm",
]


def _build_unit_atom_pattern(
) -> str:
    """
    构造确定性的 unit token pattern。

    长 unit 优先，
    避免例如：

        mV

    被拆成：

        m + V
    """

    # --------------------------------------------------------
    # Unicode micro aliases
    #
    # Scientific PDFs commonly contain either:
    #
    #     μ  U+03BC GREEK SMALL LETTER MU
    #     µ  U+00B5 MICRO SIGN
    #
    # They are visually almost identical but regex matching
    # treats them as different characters.
    #
    # Keep UNIT_BASES canonical and generate aliases here.
    # --------------------------------------------------------

    unit_bases = set(
        UNIT_BASES
    )

    for unit in tuple(
        unit_bases
    ):

        if "μ" in unit:

            unit_bases.add(
                unit.replace(
                    "μ",
                    "µ",
                )
            )

    escaped = [
        re.escape(unit)
        for unit in sorted(
            unit_bases,
            key=len,
            reverse=True,
        )
    ]

    base_pattern = (
        "(?:"
        + "|".join(escaped)
        + ")"
    )

    # 支持：
    #
    # cm2
    # cm^2
    # cm²
    # cm−2
    # cm^-2
    #
    exponent = r"""
    (?:
        \^?[+\-−]?\d+
        |
        [⁺⁻]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+
    )?
    """

    return (
        f"(?:{base_pattern}{exponent})"
    )


UNIT_ATOM_PATTERN = (
    _build_unit_atom_pattern()
)


# Compound units:
#
# μW/cm²
# W m−2
# J/cm³
# pC/N
# C/m²
# V/μm
#
UNIT_PATTERN = rf"""
{UNIT_ATOM_PATTERN}
(?:
    \s*
    (?:
        /
        |
        ·
        |
        ⋅
        |
        \*
    )
    \s*
    {UNIT_ATOM_PATTERN}
    |
    \s+
    {UNIT_ATOM_PATTERN}
)*

# 单位不能只是普通英文单词或更长
# alphanumeric token 的前缀。
#
# 防止：
#
# Figure 3 shows
#        ↓
#       3 s
#
# 以及：
#
# 8.22 mW cm2
#          ↓
#         cm
#
# 当完整 cm2 因回溯没有被采用时，
# 不允许退化成 prefix match。
#
(?!
    [A-Za-z0-9]
    |
    [\x00-\x08\x0B\x0C\x0E-\x1F\x7F]+\d
)
"""


RANGE_SEPARATOR_PATTERN = r"""
(?:
    -
    |
    –
    |
    —
    |
    −
    |
    ~
    |
    ～
    |
    (?i:\bto\b)
)
"""


RANGE_PATTERN = re.compile(
    rf"""
    (?P<value_min>
        {NUMBER_PATTERN}
    )

    \s*

    {RANGE_SEPARATOR_PATTERN}

    \s*

    (?P<value_max>
        {NUMBER_PATTERN}
    )

    \s*

    (?P<unit>
        {UNIT_PATTERN}
    )
    """,
    flags=re.VERBOSE,
)


SCALAR_PATTERN = re.compile(
    rf"""
    (?P<value>
        {NUMBER_PATTERN}
    )

    \s*

    (?P<unit>
        {UNIT_PATTERN}
    )
    """,
    flags=re.VERBOSE,
)


# ============================================================
# Scanner models
# ============================================================


@dataclass(frozen=True)
class NumericMention:
    page_number: int

    mention_key: str

    raw_text: str

    value_type: str

    raw_value: float | None

    raw_value_min: float | None

    raw_value_max: float | None

    raw_unit: str | None

    sentence_text: str

    context_text: str

    def to_record(
        self,
    ) -> dict:
        return {
            "page_number":
                self.page_number,

            "mention_key":
                self.mention_key,

            "raw_text":
                self.raw_text,

            "value_type":
                self.value_type,

            "raw_value":
                self.raw_value,

            "raw_value_min":
                self.raw_value_min,

            "raw_value_max":
                self.raw_value_max,

            "raw_unit":
                self.raw_unit,

            "sentence_text":
                self.sentence_text,

            "context_text":
                self.context_text,
        }


# ============================================================
# Text helpers
# ============================================================


def parse_number(
    text: str,
) -> float:
    """
    将 scanner 捕获的普通数字转换为 float。
    """

    cleaned = (
        text
        .replace(",", "")
        .strip()
    )

    return float(
        cleaned
    )


def normalize_unit_text(
    text: str,
) -> str:
    """
    只做显示层面的 whitespace normalization。

    这里不执行 Pint unit conversion，
    也不猜测 PDF control character 的科学含义。
    """

    cleaned = re.sub(
        r"\s+",
        " ",
        text,
    )

    return cleaned.strip()


def extract_sentence(
    text: str,
    start: int,
    end: int,
) -> str:
    """
    获取包含 mention 的近似句子。

    PDF page text 中换行通常只是排版换行，
    因此不把 '\\n' 当作句子边界。

    同时避免把小数点：

        84.5
        0.46

    中的 "." 误认为 sentence boundary。
    """

    def is_decimal_period(
        position: int,
    ) -> bool:

        if (
            position <= 0
            or position
            >= len(text) - 1
        ):

            return False

        return (
            text[
                position - 1
            ].isdigit()
            and text[
                position + 1
            ].isdigit()
        )

    # --------------------------------------------------------
    # Left boundary
    # --------------------------------------------------------

    sentence_start = 0

    for position in range(
        start - 1,
        -1,
        -1,
    ):

        character = text[
            position
        ]

        if character == ".":

            if is_decimal_period(
                position
            ):

                continue

            sentence_start = (
                position + 1
            )

            break

        if character in (
            "!",
            "?",
            "。",
            "！",
            "？",
        ):

            sentence_start = (
                position + 1
            )

            break

    # --------------------------------------------------------
    # Right boundary
    # --------------------------------------------------------

    sentence_end = len(
        text
    )

    for position in range(
        end,
        len(text),
    ):

        character = text[
            position
        ]

        if character == ".":

            if is_decimal_period(
                position
            ):

                continue

            sentence_end = (
                position + 1
            )

            break

        if character in (
            "!",
            "?",
            "。",
            "！",
            "？",
        ):

            sentence_end = (
                position + 1
            )

            break

    sentence = text[
        sentence_start:
        sentence_end
    ]

    # PDF line wrapping 不属于语义。
    sentence = re.sub(
        r"\s+",
        " ",
        sentence,
    )

    return sentence.strip()


def extract_context(
    text: str,
    start: int,
    end: int,
    radius: int = 180,
) -> str:
    """
    返回 mention 左右固定字符窗口。
    """

    context_start = max(
        0,
        start - radius,
    )

    context_end = min(
        len(text),
        end + radius,
    )

    return (
        text[
            context_start:
            context_end
        ]
        .strip()
    )


def spans_overlap(
    left: tuple[int, int],
    right: tuple[int, int],
) -> bool:

    return (
        left[0] < right[1]
        and right[0] < left[1]
    )

def is_figure_panel_label(
    *,
    text: str,
    start: int,
    end: int,
) -> bool:
    """
    判断当前 numeric-looking token
    是否实际上是 Figure panel label。

    例如：

        Figure 2C
        Figure 5g
        Fig. 3A
        Figure S2C

    这些不是：

        2 C
        5 g

    这样的物理量。

    这里只过滤明确的文档结构噪声，
    不做 metric-specific 判断。
    """

    raw_text = text[
        start:end
    ]

    # 真正写成：
    #
    # 5 g
    # 2 C
    #
    # 的量值保留。
    if re.search(
        r"\s",
        raw_text,
    ):

        return False

    prefix = text[
        max(
            0,
            start - 40,
        ):
        start
    ]

    figure_pattern = re.compile(
        r"""
        \b
        (?:
            Figure
            |
            Fig\.
            |
            Fig
        )
        \s*
        [A-Za-z]?
        \s*
        $
        """,
        flags=(
            re.VERBOSE
            | re.IGNORECASE
        ),
    )

    return (
        figure_pattern.search(
            prefix
        )
        is not None
    )

# ============================================================
# Page scanner
# ============================================================


def scan_page_numeric_mentions(
    *,
    page_number: int,
    text: str,
) -> list[NumericMention]:
    """
    扫描单页文本中的“数字 + 显式单位”。

    扫描顺序：

    1. Range
    2. Scalar

    Scalar 如果落在已有 Range span 内则跳过，
    防止：

        10-20 kV/mm

    同时生成：

        range
        10 kV/mm
        20 kV/mm
    """

    if not text.strip():

        return []

    mentions: list[
        NumericMention
    ] = []

    occupied_spans: list[
        tuple[int, int]
    ] = []

    # ========================================================
    # 1. Range
    # ========================================================

    for match in (
        RANGE_PATTERN.finditer(
            text
        )
    ):

        start, end = (
            match.span()
        )

        raw_text = (
            match.group(0)
            .strip()
        )

        unit = normalize_unit_text(
            match.group(
                "unit"
            )
        )

        mention = NumericMention(
            page_number=page_number,

            mention_key=(
                f"p{page_number}:"
                f"{start}:{end}"
            ),

            raw_text=raw_text,

            value_type="range",

            raw_value=None,

            raw_value_min=parse_number(
                match.group(
                    "value_min"
                )
            ),

            raw_value_max=parse_number(
                match.group(
                    "value_max"
                )
            ),

            raw_unit=unit,

            sentence_text=(
                extract_sentence(
                    text,
                    start,
                    end,
                )
            ),

            context_text=(
                extract_context(
                    text,
                    start,
                    end,
                )
            ),
        )

        mentions.append(
            mention
        )

        occupied_spans.append(
            (
                start,
                end,
            )
        )

    # ========================================================
    # 2. Scalar
    # ========================================================

    for match in (
        SCALAR_PATTERN.finditer(
            text
        )
    ):

        start, end = (
            match.span()
        )

        current_span = (
            start,
            end,
        )

        if is_figure_panel_label(
            text=text,
            start=start,
            end=end,
        ):

            continue

        if any(
            spans_overlap(
                current_span,
                occupied_span,
            )
            for occupied_span
            in occupied_spans
        ):

            continue

        raw_text = (
            match.group(0)
            .strip()
        )

        unit = normalize_unit_text(
            match.group(
                "unit"
            )
        )

        mention = NumericMention(
            page_number=page_number,

            mention_key=(
                f"p{page_number}:"
                f"{start}:{end}"
            ),

            raw_text=raw_text,

            value_type="scalar",

            raw_value=parse_number(
                match.group(
                    "value"
                )
            ),

            raw_value_min=None,

            raw_value_max=None,

            raw_unit=unit,

            sentence_text=(
                extract_sentence(
                    text,
                    start,
                    end,
                )
            ),

            context_text=(
                extract_context(
                    text,
                    start,
                    end,
                )
            ),
        )

        mentions.append(
            mention
        )

    mentions.sort(
        key=lambda item:
            item.mention_key
    )

    return mentions


# ============================================================
# SQLite source
# ============================================================


def get_document_pages(
    document_id: str,
) -> list[dict]:
    """
    读取某篇论文所有 page text。

    Numeric scanner 使用 pages，
    不使用 chunks。

    原因：
    chunks 存在 overlap，
    直接扫描 chunks 会产生重复 mention。
    """

    connection = get_connection()

    try:

        connection.row_factory = (
            __import__(
                "sqlite3"
            ).Row
        )

        cursor = connection.execute(
            """
            SELECT
                page_number,
                text

            FROM pages

            WHERE document_id = ?

            ORDER BY page_number
            """,
            (
                document_id,
            ),
        )

        return [
            dict(row)
            for row
            in cursor.fetchall()
        ]

    finally:

        connection.close()


def get_documents_for_numeric_scan(
) -> list[dict]:
    """
    获取 Numeric Scan 所需的 document identity。

    content_hash 用于增量生命周期判断。
    """

    connection = get_connection()

    try:

        connection.row_factory = (
            __import__(
                "sqlite3"
            ).Row
        )

        cursor = connection.execute(
            """
            SELECT
                id,
                title,
                filename,
                content_hash

            FROM documents

            ORDER BY title
            """
        )

        return [
            dict(row)
            for row
            in cursor.fetchall()
        ]

    finally:

        connection.close()


# ============================================================
# Document scanner
# ============================================================


def scan_document_numeric_mentions(
    document_id: str,
) -> list[dict]:
    """
    扫描一篇论文全部 pages。
    """

    records = []

    pages = get_document_pages(
        document_id
    )

    for page in pages:

        mentions = (
            scan_page_numeric_mentions(
                page_number=(
                    page[
                        "page_number"
                    ]
                ),

                text=(
                    page.get(
                        "text"
                    )
                    or ""
                ),
            )
        )

        records.extend(
            mention.to_record()
            for mention
            in mentions
        )

    return records


# ============================================================
# Incremental library scanner
# ============================================================


def update_numeric_mentions(
    *,
    detector_version: str = (
        DETECTOR_VERSION
    ),
    limit: int | None = None,
) -> dict:
    """
    对整个知识库执行增量 Numeric Scan。

    已经满足：

        same document_id
        same content_hash
        same detector_version
        status=success

    的文档直接跳过。

    limit:
        最多扫描多少篇当前需要扫描的文档。
    """

    if (
        limit is not None
        and limit <= 0
    ):

        raise ValueError(
            "limit 必须大于 0。"
        )

    documents = (
        get_documents_for_numeric_scan()
    )

    total_documents = len(
        documents
    )

    cached_documents = 0
    scanned_documents = 0
    deferred_documents = 0
    mention_count = 0

    for index, document in enumerate(
        documents,
        start=1,
    ):

        document_id = (
            document["id"]
        )

        content_hash = (
            document.get(
                "content_hash"
            )
        )

        if not content_hash:

            print(
                f"[{index}/{total_documents}] "
                "[SKIP:NO_HASH] "
                f"{document['title']}"
            )

            deferred_documents += 1

            continue

        current = (
            has_current_numeric_scan(
                document_id=document_id,

                content_hash=(
                    content_hash
                ),

                detector_version=(
                    detector_version
                ),
            )
        )

        if current:

            print(
                f"[{index}/{total_documents}] "
                "[NUMERIC:CACHED] "
                f"{document['title']}"
            )

            cached_documents += 1

            continue

        if (
            limit is not None
            and scanned_documents
            >= limit
        ):

            deferred_documents += 1

            continue

        print(
            f"[{index}/{total_documents}] "
            "[NUMERIC:SCAN] "
            f"{document['title']}"
        )

        mentions = (
            scan_document_numeric_mentions(
                document_id
            )
        )

        replace_numeric_scan_result(
            document_id=document_id,

            content_hash=(
                content_hash
            ),

            detector_version=(
                detector_version
            ),

            mentions=mentions,
        )

        scanned_documents += 1

        mention_count += len(
            mentions
        )

    completed_documents = (
        cached_documents
        + scanned_documents
    )

    return {
        "detector_version":
            detector_version,

        "total_documents":
            total_documents,

        "cached_documents":
            cached_documents,

        "scanned_documents":
            scanned_documents,

        "deferred_documents":
            deferred_documents,

        "completed_documents":
            completed_documents,

        "new_mentions":
            mention_count,

        "coverage_complete":
            (
                completed_documents
                == total_documents
            ),
    }