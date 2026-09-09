import re

from dataclasses import dataclass

from app.enrichment.unit_signature import (
    build_unit_signature,
)


ONTOLOGY_VERSION = (
    "metric-ontology-v1"
)


@dataclass(frozen=True)
class MetricOntologySpec:

    key: str

    display_name: str

    dimension_unit: str

    canonical_unit: str | None

    aliases: tuple[str, ...]

    positive_terms: tuple[str, ...]

    negative_terms: tuple[str, ...]


# ============================================================
# Canonical Metric Ontology
#
# 注意：
#
# 这里定义的是科学语义 ontology，
# 不等于最终 classification result。
#
# 同一个 dimensionality 可以对应多个 metric。
# ============================================================

METRIC_ONTOLOGY = {

    # --------------------------------------------------------
    # Area power density
    # --------------------------------------------------------

    "power_density": MetricOntologySpec(
        key="power_density",

        display_name=(
            "输出面积功率密度"
        ),

        dimension_unit="W/m^2",

        canonical_unit="W/m²",

        aliases=(
            "power_density",
            "area_power_density",
            "areal_power_density",
            "output_power_density",
        ),

        positive_terms=(
            "power density",
            "output power density",
            "peak power density",
            "maximum power density",
            "areal power density",
            "areal peak power density",
            "power per unit area",
        ),

        negative_terms=(
            "incident power",
            "incident light",
            "incident solar",
            "illumination power",
            "solar simulator",
            "light intensity",
            "irradiance",
            "energy density",
        ),
    ),

    # --------------------------------------------------------
    # Incident / illumination power density
    # --------------------------------------------------------

    "incident_power_density":
        MetricOntologySpec(
            key=(
                "incident_power_density"
            ),

            display_name=(
                "入射功率密度"
            ),

            dimension_unit="W/m^2",

            canonical_unit="W/m²",

            aliases=(
                "incident_power_density",
                "illumination_power_density",
                "solar_power_density",
                "irradiance",
            ),

            positive_terms=(
                "incident power",
                "incident light",
                "incident solar",
                "illumination power",
                "solar simulator",
                "light intensity",
                "irradiance",
                "1 sun",
                "one sun",
            ),

            negative_terms=(
                "output power density",
                "peak power density",
                "maximum power density",
                "areal power density",
            ),
        ),

    # --------------------------------------------------------
    # Volumetric power density
    # --------------------------------------------------------

    "volumetric_power_density":
        MetricOntologySpec(
            key=(
                "volumetric_power_density"
            ),

            display_name=(
                "体积功率密度"
            ),

            dimension_unit="W/m^3",

            canonical_unit="W/m³",

            aliases=(
                "volumetric_power_density",
                "volume_power_density",
            ),

            positive_terms=(
                "power density",
                "volumetric power density",
                "volume power density",
                "power per unit volume",
            ),

            negative_terms=(
                "energy density",
            ),
        ),

    # --------------------------------------------------------
    # Energy density
    #
    # 注意：
    #
    # J/m³ 与 Pa 的 dimensionality 相同，
    # 所以绝不能仅凭 dimensionality
    # 自动判断成 energy_density。
    # --------------------------------------------------------

    "energy_density":
        MetricOntologySpec(
            key="energy_density",

            display_name="储能密度",

            dimension_unit="J/m^3",

            canonical_unit="J/cm³",

            aliases=(
                "energy_density",
                "energy_storage_density",
                "discharged_energy_density",
            ),

            positive_terms=(
                "energy density",
                "energy storage density",
                "stored energy density",
                "discharged energy density",
                "recoverable energy density",
            ),

            negative_terms=(
                "pressure",
                "stress",
                "compressive stress",
                "tensile stress",
                "power density",
            ),
        ),

    # --------------------------------------------------------
    # Pressure / stress
    # --------------------------------------------------------

    "pressure":
        MetricOntologySpec(
            key="pressure",

            display_name="压力",

            dimension_unit="Pa",

            canonical_unit="Pa",

            aliases=(
                "pressure",
                "applied_pressure",
            ),

            positive_terms=(
                "pressure",
                "applied pressure",
                "air pressure",
                "contact pressure",
            ),

            negative_terms=(
                "energy density",
                "energy storage density",
            ),
        ),

    "stress":
        MetricOntologySpec(
            key="stress",

            display_name="应力",

            dimension_unit="Pa",

            canonical_unit="Pa",

            aliases=(
                "stress",
                "mechanical_stress",
                "compressive_stress",
                "tensile_stress",
            ),

            positive_terms=(
                "stress",
                "mechanical stress",
                "compressive stress",
                "tensile stress",
            ),

            negative_terms=(
                "energy density",
            ),
        ),

    # --------------------------------------------------------
    # Electric field
    # --------------------------------------------------------

    "breakdown_strength":
        MetricOntologySpec(
            key=(
                "breakdown_strength"
            ),

            display_name="击穿场强",

            dimension_unit="V/m",

            canonical_unit="MV/m",

            aliases=(
                "breakdown_strength",
                "breakdown_field",
                "breakdown_electric_field",
            ),

            positive_terms=(
                "breakdown strength",
                "breakdown field",
                "breakdown electric field",
                "electric breakdown",
            ),

            negative_terms=(
                "applied field",
                "poling field",
            ),
        ),

    "electric_field":
        MetricOntologySpec(
            key="electric_field",

            display_name="电场强度",

            dimension_unit="V/m",

            canonical_unit="MV/m",

            aliases=(
                "electric_field",
                "applied_electric_field",
                "poling_field",
            ),

            positive_terms=(
                "electric field",
                "applied field",
                "applied electric field",
                "poling field",
                "field strength",
            ),

            negative_terms=(
                "breakdown field",
                "breakdown strength",
            ),
        ),

    # --------------------------------------------------------
    # Voltage
    # --------------------------------------------------------

    "output_voltage":
        MetricOntologySpec(
            key="output_voltage",

            display_name="输出电压",

            dimension_unit="V",

            canonical_unit="V",

            aliases=(
                "output_voltage",
                "open_circuit_voltage",
                "open-circuit_voltage",
            ),

            positive_terms=(
                "output voltage",
                "open circuit voltage",
                "open-circuit voltage",
                "peak voltage",
                "generated voltage",
            ),

            negative_terms=(
                "applied voltage",
                "input voltage",
                "bias voltage",
                "charging voltage",
            ),
        ),

    "applied_voltage":
        MetricOntologySpec(
            key="applied_voltage",

            display_name="施加电压",

            dimension_unit="V",

            canonical_unit="V",

            aliases=(
                "applied_voltage",
                "input_voltage",
                "bias_voltage",
            ),

            positive_terms=(
                "applied voltage",
                "input voltage",
                "bias voltage",
                "voltage applied",
            ),

            negative_terms=(
                "output voltage",
                "open circuit voltage",
                "open-circuit voltage",
            ),
        ),

    # --------------------------------------------------------
    # Piezoelectric charge coefficient
    # --------------------------------------------------------

    "piezoelectric_charge_coefficient":
        MetricOntologySpec(
            key=(
                "piezoelectric_charge_coefficient"
            ),

            display_name=(
                "压电电荷系数"
            ),

            dimension_unit="C/N",

            canonical_unit="pC/N",

            aliases=(
                "piezoelectric_charge_coefficient",
                "d33",
                "d31",
                "d15",
                "dynamic_d33",
            ),

            positive_terms=(
                "piezoelectric coefficient",
                "piezoelectric charge coefficient",
                "d33",
                "d31",
                "d15",
            ),

            negative_terms=(),
        ),

    # --------------------------------------------------------
    # Frequency
    # --------------------------------------------------------

    "frequency":
        MetricOntologySpec(
            key="frequency",

            display_name="频率",

            dimension_unit="Hz",

            canonical_unit="Hz",

            aliases=(
                "frequency",
                "resonant_frequency",
                "excitation_frequency",
            ),

            positive_terms=(
                "frequency",
                "resonant frequency",
                "resonance frequency",
                "excitation frequency",
            ),

            negative_terms=(),
        ),

    # --------------------------------------------------------
    # Power
    # --------------------------------------------------------

    "power":
        MetricOntologySpec(
            key="power",

            display_name="功率",

            dimension_unit="W",

            canonical_unit="W",

            aliases=(
                "power",
                "output_power",
                "peak_power",
            ),

            positive_terms=(
                "power",
                "output power",
                "peak power",
                "maximum power",
            ),

            negative_terms=(
                "power density",
            ),
        ),

    # --------------------------------------------------------
    # Current
    # --------------------------------------------------------

    "current":
        MetricOntologySpec(
            key="current",

            display_name="电流",

            dimension_unit="A",

            canonical_unit="A",

            aliases=(
                "current",
                "output_current",
                "short_circuit_current",
            ),

            positive_terms=(
                "current",
                "output current",
                "short circuit current",
                "short-circuit current",
            ),

            negative_terms=(
                "current density",
            ),
        ),
}


def dimensionality_for_unit(
    unit: str,
) -> str:
    """
    利用 Unit Signature Layer 得到 ontology
    所需 dimensionality。

    避免手写 Pint dimensionality 字符串。
    """

    signature = build_unit_signature(
        unit
    )

    if (
        signature.parse_status
        != "valid"
        or
        signature.dimensionality
        is None
    ):

        raise ValueError(
            f"Ontology dimension unit "
            f"无法解析：{unit}"
        )

    return signature.dimensionality


def get_metric_spec(
    metric_key: str,
) -> MetricOntologySpec:

    if metric_key not in (
        METRIC_ONTOLOGY
    ):

        raise ValueError(
            f"Unknown ontology metric: "
            f"{metric_key}"
        )

    return METRIC_ONTOLOGY[
        metric_key
    ]


def resolve_metric_alias(
    metric_name: str,
) -> str:
    """
    将历史 alias 映射到 canonical metric key。

    例如：

        area_power_density
        areal_power_density

    都统一为：

        power_density
    """

    normalized = (
        metric_name
        .strip()
        .lower()
    )

    for key, spec in (
        METRIC_ONTOLOGY.items()
    ):

        if normalized == key:

            return key

        if normalized in (
            alias.lower()
            for alias
            in spec.aliases
        ):

            return key

    raise ValueError(
        f"Unknown metric alias: "
        f"{metric_name}"
    )


def get_candidate_metric_keys(
    *,
    dimensionality: str,
) -> list[str]:
    """
    只根据 dimensionality 生成 candidate set。

    注意：

        candidate != classification

    例如：

        J/m³
        Pa

    dimensionality 相同，所以必须同时返回
    energy_density / pressure / stress。
    """

    candidates = []

    for key, spec in (
        METRIC_ONTOLOGY.items()
    ):

        spec_dimension = (
            dimensionality_for_unit(
                spec.dimension_unit
            )
        )

        if (
            spec_dimension
            == dimensionality
        ):

            candidates.append(
                key
            )

    return sorted(
        set(
            candidates
        )
    )


def normalize_metric_context_text(
    text: str,
) -> str:
    """
    将 PDF extraction 产生的排版噪声转换成
    更稳定的 lexical matching representation。

    例如：

        power den- sity
        -> power density

        open-circuit voltage
        -> open circuit voltage

        open−circuit voltage
        -> open circuit voltage

    这里只用于 context routing，
    不修改数据库中的原始 evidence。
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

    # PDF line wrapping:
    #
    # den- sity -> density
    # maxi- mum  -> maximum
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

    # 剩余真正的 lexical hyphen
    # 统一为空格：
    #
    # open-circuit
    # -> open circuit
    normalized = normalized.replace(
        "-",
        " ",
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    ).strip()

    return normalized

def score_metric_context(
    *,
    metric_key: str,
    text: str,
) -> int:
    """
    deterministic lexical score。

    positive term:
        +2

    negative term:
        -3

    注意：

    score 只是 routing evidence，
    score == 0 绝不能被视为 classification。
    """

    spec = get_metric_spec(
        metric_key
    )

    normalized_text = (
        normalize_metric_context_text(
            text
        )
    )

    score = 0

    for term in (
        spec.positive_terms
    ):

        normalized_term = (
            normalize_metric_context_text(
                term
            )
        )

        if (
            normalized_term
            in normalized_text
        ):

            score += 2

    for term in (
        spec.negative_terms
    ):

        normalized_term = (
            normalize_metric_context_text(
                term
            )
        )

        if (
            normalized_term
            in normalized_text
        ):

            score -= 3

    return score


def rank_metric_candidates(
    *,
    raw_unit: str,
    text: str,
) -> list[tuple[str, int]]:
    """
    raw_unit
        ↓
    dimensionality
        ↓
    candidate metrics
        ↓
    deterministic context ranking
    """

    signature = build_unit_signature(
        raw_unit
    )

    if (
        signature.parse_status
        not in {
            "valid",
            "custom",
        }
        or
        signature.dimensionality
        is None
    ):

        return []

    candidates = (
        get_candidate_metric_keys(
            dimensionality=(
                signature.dimensionality
            )
        )
    )

    ranked = [
        (
            metric_key,
            score_metric_context(
                metric_key=metric_key,
                text=text,
            ),
        )
        for metric_key
        in candidates
    ]

    return sorted(
        ranked,
        key=lambda item: (
            -item[1],
            item[0],
        ),
    )

def select_metric_candidate(
    *,
    raw_unit: str,
    text: str,
    min_score: int = 1,
) -> str | None:
    """
    从 deterministic routing 结果中选择
    高置信 metric。

    返回 None 表示：

        unsupported
        无正向 lexical evidence
        top candidate 并列

    绝不使用 alphabetical tie-break
    伪造 classification。
    """

    ranked = rank_metric_candidates(
        raw_unit=raw_unit,
        text=text,
    )

    if not ranked:

        return None

    top_key, top_score = (
        ranked[0]
    )

    if top_score < min_score:

        return None

    if len(ranked) > 1:

        second_score = (
            ranked[1][1]
        )

        if (
            second_score
            == top_score
        ):

            return None

    return top_key