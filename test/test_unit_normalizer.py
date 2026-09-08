from app.extraction.schemas import (
    ExtractedFact,
)

from app.extraction.metric_registry import (
    get_metric_spec,
)

from app.extraction.unit_normalizer import (
    normalize_fact,
)


def make_fact(
    metric_name: str,
    value_type: str,
    value: float | None,
    unit: str,
    value_min: float | None = None,
    value_max: float | None = None,
):

    return ExtractedFact(
        document_id="test",

        metric_name=metric_name,

        value_type=value_type,

        value=value,

        value_min=value_min,

        value_max=value_max,

        unit=unit,

        page_number=1,

        chunk_id=1,

        evidence="test",

        evidence_verified=True,

        condition_text=None,

        provenance="author_result",

        confidence=1.0,
    )


def test_unit_normalizer():

    test_cases = [

        make_fact(
            "power_density",
            "scalar",
            10.1,
            "μW/cm²",
        ),

        make_fact(
            "power_density",
            "scalar",
            8.22,
            "mW/cm²",
        ),

        make_fact(
            "power_density",
            "scalar",
            13.5,
            "mW/cm²",
        ),

        make_fact(
            "energy_density",
            "scalar",
            14.2,
            "J/cm³",
        ),

        make_fact(
            "breakdown_strength",
            "scalar",
            560,
            "MV/m",
        ),
    ]

    for fact in test_cases:

        metric_spec = get_metric_spec(
            fact.metric_name
        )

        normalized = normalize_fact(
            fact,
            metric_spec,
        )

        print("=" * 60)

        print(
            f"原始："
            f"{fact.value} "
            f"{fact.unit}"
        )

        print(
            "归一化：",
            normalized.value,
            normalized.unit,
        )

        print(
            "Converted:",
            normalized.converted,
        )

        print(
            "Error:",
            normalized.error,
        )


if __name__ == "__main__":
    test_unit_normalizer()