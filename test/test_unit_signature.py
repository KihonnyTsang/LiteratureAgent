import math

from app.enrichment.unit_signature import (
    build_unit_signature,
)


def test_area_power_density_variants_share_signature():

    variants = [
        "μW/cm2",
        "μW/cm²",
        "μW cm−2",
    ]

    signatures = [
        build_unit_signature(
            unit
        )
        for unit
        in variants
    ]

    assert all(
        item.parse_status
        == "valid"
        for item
        in signatures
    )

    assert len({
        item.dimensionality
        for item
        in signatures
    }) == 1

    assert len({
        item.base_unit
        for item
        in signatures
    }) == 1

    first_scale = (
        signatures[0]
        .scale_to_base
    )

    assert first_scale is not None

    for item in signatures[1:]:

        assert (
            item.scale_to_base
            is not None
        )

        assert math.isclose(
            item.scale_to_base,
            first_scale,
            rel_tol=1e-12,
            abs_tol=1e-12,
        )


def test_electric_field_variants_share_signature():

    left = build_unit_signature(
        "MV/m"
    )

    right = build_unit_signature(
        "MV m−1"
    )

    assert (
        left.parse_status
        == "valid"
    )

    assert (
        right.parse_status
        == "valid"
    )

    assert (
        left.dimensionality
        == right.dimensionality
    )

    assert (
        left.base_unit
        == right.base_unit
    )

    assert math.isclose(
        left.scale_to_base,
        right.scale_to_base,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )


def test_inverse_centimeter_is_valid():

    signature = (
        build_unit_signature(
            "cm−1"
        )
    )

    assert (
        signature.parse_status
        == "valid"
    )

    assert (
        signature.parse_error
        is None
    )


def test_piezoelectric_coefficient_unit_is_valid():

    signature = (
        build_unit_signature(
            "pC/N"
        )
    )

    assert (
        signature.parse_status
        == "valid"
    )

    assert (
        signature.dimensionality
        is not None
    )


def test_spaced_weight_percent_is_custom():

    left = build_unit_signature(
        "wt%"
    )

    right = build_unit_signature(
        "wt %"
    )

    assert (
        left.parse_status
        == "custom"
    )

    assert (
        right.parse_status
        == "custom"
    )

    assert (
        left.normalized_unit_text
        == "wt%"
    )

    assert (
        right.normalized_unit_text
        == "wt%"
    )

    assert (
        left.scale_to_base
        == 0.01
    )


def test_suspicious_j1011_is_invalid():

    signature = (
        build_unit_signature(
            "J1011"
        )
    )

    assert (
        signature.parse_status
        == "invalid"
    )


def test_suspicious_a1_is_invalid():

    signature = (
        build_unit_signature(
            "A1"
        )
    )

    assert (
        signature.parse_status
        == "invalid"
    )


def test_unit_signature_does_not_assign_metric():

    signature = (
        build_unit_signature(
            "V"
        )
    )

    assert (
        signature.parse_status
        == "valid"
    )

    # Unit Signature 层只描述物理单位，
    # 不判断 output / applied / coercive voltage。
    assert not hasattr(
        signature,
        "metric_key",
    )

def test_inverse_piezoelectric_notation_is_valid():

    left = build_unit_signature(
        "pC/N"
    )

    right = build_unit_signature(
        "pC N−1"
    )

    assert (
        right.parse_status
        == "valid"
    )

    assert (
        left.dimensionality
        == right.dimensionality
    )

    assert (
        left.base_unit
        == right.base_unit
    )


def test_acceleration_variants_share_signature():

    variants = [
        "m s−2",
        "m/s2",
        "ms−2",
    ]

    signatures = [
        build_unit_signature(
            unit
        )
        for unit in variants
    ]

    assert all(
        item.parse_status
        == "valid"
        for item
        in signatures
    )

    assert len({
        item.dimensionality
        for item
        in signatures
    }) == 1

    assert len({
        item.base_unit
        for item
        in signatures
    }) == 1


def test_celsius_symbol_is_valid():

    signature = (
        build_unit_signature(
            "℃"
        )
    )

    assert (
        signature.parse_status
        == "valid"
    )

    assert (
        signature.dimensionality
        is not None
    )


def test_plain_area_unit_is_supported():

    signature = (
        build_unit_signature(
            "km2"
        )
    )

    assert (
        signature.parse_status
        == "valid"
    )

    assert (
        signature.normalized_unit_text
        == "km^2"
    )


def test_middle_dot_power_density_is_supported():

    left = build_unit_signature(
        "mW/cm²"
    )

    right = build_unit_signature(
        "mW·cm−2"
    )

    assert (
        right.parse_status
        == "valid"
    )

    assert (
        left.dimensionality
        == right.dimensionality
    )

    assert (
        left.base_unit
        == right.base_unit
    )


def test_thermal_conductivity_chain_is_valid():

    signature = (
        build_unit_signature(
            "W m−1 K−1"
        )
    )

    assert (
        signature.parse_status
        == "valid"
    )

    assert (
        signature.parse_error
        is None
    )


def test_fourth_power_charge_compound_is_valid():

    signature = (
        build_unit_signature(
            "m4/C2"
        )
    )

    assert (
        signature.parse_status
        == "valid"
    )

    assert (
        "m^4"
        in signature.normalized_unit_text
    )

    assert (
        "C^2"
        in signature.normalized_unit_text
    )