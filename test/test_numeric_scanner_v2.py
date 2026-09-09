from app.enrichment.numeric_scanner import (
    DETECTOR_VERSION,
    SCALAR_PATTERN,
    normalize_unit_text,
)


def get_scalar_match(
    text: str,
):
    match = SCALAR_PATTERN.search(
        text
    )

    assert match is not None

    return match


def test_detector_version_is_v2():

    assert (
        DETECTOR_VERSION
        == "numeric-v2"
    )


def test_micro_sign_power_density_is_recognized():

    match = get_scalar_match(
        "power density of "
        "1.48 µW cm−3"
    )

    assert (
        match.group("value")
        == "1.48"
    )

    assert (
        match.group("unit")
        == "µW cm−3"
    )


def test_plain_digit_area_exponent_is_not_truncated():

    match = get_scalar_match(
        "power density of "
        "8.22 mW cm2"
    )

    assert (
        match.group("value")
        == "8.22"
    )

    assert (
        match.group("unit")
        == "mW cm2"
    )


def test_existing_greek_mu_behavior_is_preserved():

    match = get_scalar_match(
        "peak output power density "
        "41.02 μW/cm2"
    )

    assert (
        match.group("value")
        == "41.02"
    )

    assert (
        match.group("unit")
        == "μW/cm2"
    )

def test_pdf_control_character_does_not_invent_unit_exponent():

    match = get_scalar_match(
        "power density of "
        "8.22 mW cm\x032."
    )

    assert (
        match.group("value")
        == "8.22"
    )

    # U+0003 的语义未知。
    #
    # Scanner 不允许：
    #
    #     cm\x032
    #
    # 被静默转换成：
    #
    #     cm2
    #
    # 因为那会把一个可能的 cm^-2
    # 误解释成 cm^2。
    assert (
        normalize_unit_text(
            match.group("unit")
        )
        == "mW"
    )