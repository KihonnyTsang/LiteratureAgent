import re
from dataclasses import dataclass

from pint.errors import (
    OffsetUnitCalculusError,
)

from app.extraction.unit_normalizer import (
    normalize_unit_text as normalize_fact_unit_text,
    ureg,
)


NORMALIZER_VERSION = (
    "unit-signature-v2"
)


# ============================================================
# Custom scientific units
# ============================================================

CUSTOM_PERCENT_UNITS = {
    "%": "%",

    "wt%": "wt%",
    "mol%": "mol%",
    "vol%": "vol%",
    "at%": "at%",
}


SUPERSCRIPT_TRANSLATION = (
    str.maketrans(
        {
            "⁰": "0",
            "¹": "1",
            "²": "2",
            "³": "3",
            "⁴": "4",
            "⁵": "5",
            "⁶": "6",
            "⁷": "7",
            "⁸": "8",
            "⁹": "9",
            "⁻": "-",
            "⁺": "+",
        }
    )
)


@dataclass(frozen=True)
class UnitSignature:

    raw_unit: str

    normalized_unit_text: str

    parse_status: str

    dimensionality: str | None

    base_unit: str | None

    scale_to_base: float | None

    parse_error: str | None

    normalizer_version: str

    def to_record(
        self,
    ) -> dict:

        return {
            "raw_unit":
                self.raw_unit,

            "normalized_unit_text":
                self.normalized_unit_text,

            "parse_status":
                self.parse_status,

            "dimensionality":
                self.dimensionality,

            "base_unit":
                self.base_unit,

            "scale_to_base":
                self.scale_to_base,

            "parse_error":
                self.parse_error,

            "normalizer_version":
                self.normalizer_version,
        }


def compact_custom_unit(
    raw_unit: str,
) -> str:
    """
    识别：

        wt%
        wt %

        mol%
        mol %
    """

    return re.sub(
        r"\s+",
        "",
        raw_unit.strip(),
    )


def _replace_negative_exponent(
    match: re.Match,
) -> str:
    """
    将：

        N-1
        s-2
        cm-3

    转换为：

        / N
        / s^2
        / cm^3
    """

    unit = match.group(
        "unit"
    )

    power = int(
        match.group(
            "power"
        )
    )

    if power == 1:

        return (
            f" / {unit}"
        )

    return (
        f" / {unit}^{power}"
    )


def normalize_scanned_unit_text(
    raw_unit: str,
) -> str:
    """
    Numeric Scanner 专用 unit syntax canonicalization。

    与 normalize_fact() 分层：

    这里只解析 unit representation，
    不判断 metric，也不做 metric-specific conversion。
    """

    text = raw_unit.strip()

    # --------------------------------------------------------
    # Unicode cleanup
    # --------------------------------------------------------

    text = (
        text
        .translate(
            SUPERSCRIPT_TRANSLATION
        )
        .replace(
            "μ",
            "u",
        )
        .replace(
            "µ",
            "u",
        )
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

    # --------------------------------------------------------
    # Multiplication dots
    #
    # pC·N−1
    # mW·cm−2
    # --------------------------------------------------------

    text = re.sub(
        r"\s*[·⋅]\s*",
        " ",
        text,
    )

    # --------------------------------------------------------
    # Celsius
    #
    # 单独 temperature:
    #
    #     25 °C
    #
    # 使用 degC。
    #
    # compound temperature difference / rate:
    #
    #     °C min−1
    #     mV °C−1
    #
    # 使用 delta_degC。
    # --------------------------------------------------------

    stripped = text.strip()

    if stripped in {
        "°C",
        "℃",
    }:

        text = "degC"

    else:

        text = (
            text
            .replace(
                "℃",
                "delta_degC",
            )
            .replace(
                "°C",
                "delta_degC",
            )
        )

    # --------------------------------------------------------
    # Percent in compound units
    #
    # % min−1
    # % °C−1
    #
    # Exact %, wt%, mol% ...
    # 已经在 custom branch 处理。
    # --------------------------------------------------------

    text = re.sub(
        r"""
        (?<![A-Za-z])
        %
        (?![A-Za-z])
        """,
        "percent",
        text,
        flags=re.VERBOSE,
    )

    # --------------------------------------------------------
    # Common PDF missing-space acceleration notation
    #
    # 0.7 ms−1
    #
    # 在科研正文中通常表示：
    #
    #     0.7 m s−1
    #
    # 而不是 inverse millisecond。
    # --------------------------------------------------------

    if text.strip() == "ms-1":

        text = "m / s"

    elif text.strip() == "ms-2":

        text = "m / s^2"

    # --------------------------------------------------------
    # Plain spatial positive powers
    #
    # cm2
    # km2
    # m3
    # m4
    #
    # 只允许 length token，
    # 避免：
    #
    # N4
    # F20
    # S12
    #
    # 被误解释成 unit exponent。
    # --------------------------------------------------------

    text = re.sub(
        r"""
        (?<![A-Za-z])
        (
            pm
            |
            nm
            |
            um
            |
            mm
            |
            cm
            |
            km
            |
            m
        )
        ([234])
        \b
        """,
        r"\1^\2",
        text,
        flags=re.VERBOSE,
    )

    # --------------------------------------------------------
    # Denominator shorthand
    #
    # m/s2
    # m4/C2
    #
    # 只在 "/" 后允许 C/s plain exponent，
    # 防止 standalone C2 被当作 Coulomb²。
    # --------------------------------------------------------

    text = re.sub(
        r"""
        /
        \s*
        (
            C
            |
            s
        )
        ([234])
        \b
        """,
        r"/ \1^\2",
        text,
        flags=re.VERBOSE,
    )

    # --------------------------------------------------------
    # Negative exponents
    #
    # pC N-1       -> pC / N
    # m s-2        -> m / s^2
    # W m-1 K-1    -> W / m / K
    # kPa-1        -> / kPa
    #
    # 只接受 1..4，
    # 所以 S-52 不会被合理化。
    # --------------------------------------------------------

    negative_exponent_pattern = (
        re.compile(
            r"""
            (?P<unit>
                delta_degC
                |
                degC
                |
                [A-Za-z_Ω]+
            )
            \s*
            \^?
            -
            (?P<power>[1-4])
            \b
            """,
            flags=re.VERBOSE,
        )
    )

    text = (
        negative_exponent_pattern
        .sub(
            _replace_negative_exponent,
            text,
        )
    )

    # 如果整个 unit 是：
    #
    #     cm-3
    #
    # 转换后会是：
    #
    #     / cm^3
    #
    # 补成：
    #
    #     1 / cm^3
    if text.lstrip().startswith(
        "/"
    ):

        text = (
            "1 "
            + text.lstrip()
        )

    # --------------------------------------------------------
    # Whitespace / slash cleanup
    # --------------------------------------------------------

    text = re.sub(
        r"\s*/\s*",
        " / ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    # --------------------------------------------------------
    # 继续复用既有 fact unit normalizer。
    #
    # 现在 negative exponent 已经转换完，
    # 不会触发其旧的 cm-2 / m-2 特殊逻辑。
    # --------------------------------------------------------

    text = (
        normalize_fact_unit_text(
            text
        )
    )

    return text


def build_custom_signature(
    *,
    raw_unit: str,
    normalized_unit: str,
    normalizer_version: str,
) -> UnitSignature:
    """
    百分比 / composition fraction。

        10 wt%
        -> 0.10 fraction
    """

    return UnitSignature(
        raw_unit=raw_unit,

        normalized_unit_text=(
            normalized_unit
        ),

        parse_status="custom",

        dimensionality=(
            "dimensionless"
        ),

        base_unit="fraction",

        scale_to_base=0.01,

        parse_error=None,

        normalizer_version=(
            normalizer_version
        ),
    )


def build_invalid_signature(
    *,
    raw_unit: str,
    normalized_unit: str,
    error: str,
    normalizer_version: str,
) -> UnitSignature:

    return UnitSignature(
        raw_unit=raw_unit,

        normalized_unit_text=(
            normalized_unit
        ),

        parse_status="invalid",

        dimensionality=None,

        base_unit=None,

        scale_to_base=None,

        parse_error=error,

        normalizer_version=(
            normalizer_version
        ),
    )


def build_unit_signature(
    raw_unit: str,
    *,
    normalizer_version: str = (
        NORMALIZER_VERSION
    ),
) -> UnitSignature:
    """
    将 raw scientific unit 转成 deterministic
    Unit Signature。

    Unit Signature 只回答：

        unit 是否能理解？
        dimensionality 是什么？
        base representation 是什么？

    不回答：

        output_voltage？
        breakdown_strength？
        energy_density？
    """

    raw_unit = raw_unit.strip()

    compact = compact_custom_unit(
        raw_unit
    )

    if compact in CUSTOM_PERCENT_UNITS:

        return build_custom_signature(
            raw_unit=raw_unit,

            normalized_unit=(
                CUSTOM_PERCENT_UNITS[
                    compact
                ]
            ),

            normalizer_version=(
                normalizer_version
            ),
        )

    normalized = (
        normalize_scanned_unit_text(
            raw_unit
        )
    )

    # --------------------------------------------------------
    # Remaining trailing digits
    #
    # legitimate:
    #
    #     km2
    #     cm3
    #     m4/C2
    #
    # 已经在 normalization 阶段变成 ^power。
    #
    # 所以剩余：
    #
    #     A1
    #     N4
    #     J1011
    #     F20
    #
    # 高概率是 formula / model / reference artifact。
    # --------------------------------------------------------

    if re.search(
        r"[A-Za-zΩ]\d+$",
        normalized,
    ):

        return build_invalid_signature(
            raw_unit=raw_unit,

            normalized_unit=(
                normalized
            ),

            error=(
                "Suspicious trailing digits "
                "in unit token."
            ),

            normalizer_version=(
                normalizer_version
            ),
        )

    try:

        parsed_unit = (
            ureg.parse_units(
                normalized
            )
        )

        dimensionality = str(
            parsed_unit.dimensionality
        )

        try:

            quantity = (
                1
                * parsed_unit
            )

            base_quantity = (
                quantity.to_base_units()
            )

            base_unit = str(
                base_quantity.units
            )

            scale_to_base = float(
                base_quantity.magnitude
            )

        except OffsetUnitCalculusError:

            # °C 是 offset unit。
            #
            # dimensionality 仍然有效，
            # 但不能用简单 multiplier
            # 表示 absolute-temperature conversion。
            base_unit = None
            scale_to_base = None

        return UnitSignature(
            raw_unit=raw_unit,

            normalized_unit_text=(
                normalized
            ),

            parse_status="valid",

            dimensionality=(
                dimensionality
            ),

            base_unit=base_unit,

            scale_to_base=(
                scale_to_base
            ),

            parse_error=None,

            normalizer_version=(
                normalizer_version
            ),
        )

    except Exception as error:

        return build_invalid_signature(
            raw_unit=raw_unit,

            normalized_unit=(
                normalized
            ),

            error=str(
                error
            ),

            normalizer_version=(
                normalizer_version
            ),
        )