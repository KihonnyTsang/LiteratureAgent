import json

from app.enrichment.metric_classifier import (
    CLASSIFIER_VERSION,
    classify_numeric_mention,
)


def make_mention(
    *,
    mention_id: int,
    raw_unit: str,
    sentence_text: str,
) -> dict:

    return {
        "id":
            mention_id,

        "raw_unit":
            raw_unit,

        "sentence_text":
            sentence_text,

        "context_text":
            sentence_text,
    }


def test_output_power_density_is_classified():

    result = classify_numeric_mention(
        make_mention(
            mention_id=1,

            raw_unit="μW/cm2",

            sentence_text=(
                "The maximum output power "
                "density reached "
                "41.02 μW/cm2."
            ),
        )
    )

    assert (
        result.status
        == "classified"
    )

    assert (
        result.metric_key
        == "power_density"
    )

    assert result.score is not None
    assert result.score > 0

    assert (
        result.classifier_version
        == CLASSIFIER_VERSION
    )


def test_incident_solar_power_density_is_classified():

    result = classify_numeric_mention(
        make_mention(
            mention_id=2,

            raw_unit="mW/cm2",

            sentence_text=(
                "An AM 1.5 solar simulator "
                "provided incident solar "
                "power density of "
                "100 mW/cm2."
            ),
        )
    )

    assert (
        result.status
        == "classified"
    )

    assert (
        result.metric_key
        == "incident_power_density"
    )


def test_volumetric_power_density_is_separate():

    result = classify_numeric_mention(
        make_mention(
            mention_id=3,

            raw_unit="µW cm−3",

            sentence_text=(
                "The device achieved "
                "a power density of "
                "1.48 µW cm−3."
            ),
        )
    )

    assert (
        result.status
        == "classified"
    )

    assert (
        result.metric_key
        == "volumetric_power_density"
    )


def test_respectively_sentence_abstains():

    result = classify_numeric_mention(
        make_mention(
            mention_id=4,

            raw_unit="J/cm3",

            sentence_text=(
                "The values reached "
                "560 MV/m and "
                "14.2 J/cm3, respectively."
            ),
        )
    )

    assert (
        result.status
        == "unresolved"
    )

    assert result.metric_key is None

    assert (
        result.reason
        == "insufficient_context"
    )


def test_unsupported_unit_is_rejected():

    result = classify_numeric_mention(
        make_mention(
            mention_id=5,

            raw_unit="A1",

            sentence_text=(
                "Figure A1 shows the result."
            ),
        )
    )

    assert (
        result.status
        == "rejected"
    )

    assert result.metric_key is None

    candidates = json.loads(
        result.candidates_json
    )

    assert candidates == []