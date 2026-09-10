from app.enrichment.metric_ontology import (
    get_candidate_metric_keys,
    rank_metric_candidates,
    resolve_metric_alias,
    select_metric_candidate,
)

from app.enrichment.unit_signature import (
    build_unit_signature,
)


def candidate_keys_for_unit(
    unit: str,
) -> list[str]:

    signature = build_unit_signature(
        unit
    )

    assert (
        signature.dimensionality
        is not None
    )

    return get_candidate_metric_keys(
        dimensionality=(
            signature.dimensionality
        )
    )


def test_power_density_aliases_are_canonicalized():

    assert (
        resolve_metric_alias(
            "area_power_density"
        )
        == "power_density"
    )

    assert (
        resolve_metric_alias(
            "areal_power_density"
        )
        == "power_density"
    )

    assert (
        resolve_metric_alias(
            "power_density"
        )
        == "power_density"
    )


def test_area_power_density_candidates():

    candidates = (
        candidate_keys_for_unit(
            "μW/cm²"
        )
    )

    assert (
        "power_density"
        in candidates
    )

    assert (
        "incident_power_density"
        in candidates
    )

    assert (
        "volumetric_power_density"
        not in candidates
    )


def test_volume_power_density_is_separate():

    candidates = (
        candidate_keys_for_unit(
            "μW/cm³"
        )
    )

    assert (
        "volumetric_power_density"
        in candidates
    )

    assert (
        "power_density"
        not in candidates
    )


def test_energy_density_and_pressure_share_dimension():

    candidates = (
        candidate_keys_for_unit(
            "J/cm³"
        )
    )

    assert (
        "energy_density"
        in candidates
    )

    assert (
        "pressure"
        in candidates
    )

    assert (
        "stress"
        in candidates
    )


def test_qiao_incident_solar_is_not_ranked_as_output():

    ranked = rank_metric_candidates(
        raw_unit="mW/cm²",

        text=(
            "The device was illuminated "
            "under an incident solar power "
            "density of 100 mW/cm² using "
            "a solar simulator."
        ),
    )

    assert ranked[0][0] == (
        "incident_power_density"
    )

    output_score = dict(
        ranked
    )[
        "power_density"
    ]

    incident_score = dict(
        ranked
    )[
        "incident_power_density"
    ]

    assert (
        incident_score
        > output_score
    )


def test_rana_output_power_density_ranks_first():

    ranked = rank_metric_candidates(
        raw_unit="μW/cm2",

        text=(
            "The device exhibited an "
            "areal peak power density of "
            "41.02 μW/cm2."
        ),
    )

    assert ranked

    assert ranked[0][0] == (
        "power_density"
    )


def test_energy_storage_density_ranks_first():

    ranked = rank_metric_candidates(
        raw_unit="J/cm³",

        text=(
            "The maximum energy storage "
            "density reached 14.2 J/cm³."
        ),
    )

    assert ranked[0][0] == (
        "energy_density"
    )


def test_breakdown_field_ranks_first():

    ranked = rank_metric_candidates(
        raw_unit="MV/m",

        text=(
            "The breakdown electric field "
            "reached 560 MV/m."
        ),
    )

    assert ranked[0][0] == (
        "breakdown_strength"
    )


def test_open_circuit_voltage_ranks_output_voltage():

    ranked = rank_metric_candidates(
        raw_unit="V",

        text=(
            "The peak-to-peak open-circuit "
            "voltage was 84.5 V."
        ),
    )

    assert ranked[0][0] == (
        "output_voltage"
    )


def test_piezoelectric_d33_candidate():

    ranked = rank_metric_candidates(
        raw_unit="pC N−1",

        text=(
            "The piezoelectric coefficient "
            "d33 reached 29 pC N−1."
        ),
    )

    assert ranked[0][0] == (
        "piezoelectric_charge_coefficient"
    )

def test_pdf_hyphenation_does_not_break_power_density():

    ranked = rank_metric_candidates(
        raw_unit="mW/cm2",

        text=(
            "We calculated the theoretical "
            "maximum power den- sity "
            "of 8.22 mW/cm2."
        ),
    )

    assert ranked

    assert (
        ranked[0][0]
        == "power_density"
    )

    assert (
        ranked[0][1]
        > 0
    )


def test_zero_score_candidate_abstains():

    selected = (
        select_metric_candidate(
            raw_unit="J/cm3",

            text=(
                "The values reached "
                "560 MV/m and "
                "14.2 J/cm3, "
                "respectively."
            ),
        )
    )

    assert selected is None


def test_strong_incident_solar_context_can_be_selected():

    selected = (
        select_metric_candidate(
            raw_unit="mW/cm2",

            text=(
                "An AM 1.5 solar simulator "
                "provided an incident solar "
                "power density of "
                "100 mW/cm2."
            ),
        )
    )

    assert (
        selected
        == "incident_power_density"
    )


def test_output_power_alias_is_separate_from_generic_power():

    assert (
        resolve_metric_alias(
            "output_power"
        )
        == "output_power"
    )

    assert (
        resolve_metric_alias(
            "power"
        )
        == "power"
    )


def test_watt_candidates_include_generic_and_output_power():

    candidates = (
        candidate_keys_for_unit(
            "mW"
        )
    )

    assert (
        "power"
        in candidates
    )

    assert (
        "output_power"
        in candidates
    )


def test_output_power_contexts_select_output_power():

    cases = [
        (
            "The device achieved a high "
            "output power of 520 mW."
        ),

        (
            "The generator can deliver "
            "peak power of 44.8 mW."
        ),

        (
            "The prototype delivered a "
            "maximum power of 2.8 mW."
        ),

        (
            "The power output from the "
            "device remained under 1 mW."
        ),

        (
            "The prototype achieved a "
            "maximum mean power of "
            "0.395 mW per footstep."
        ),

        (
            "The output power of the "
            "hybrid generator reached "
            "0.31 mW."
        ),

        (
            "The device can harvest a "
            "power output of 4.95 μW."
        ),

        (
            "The average power for "
            "charging a capacitor was "
            "81.8 nW."
        ),
    ]

    for text in cases:

        selected = (
            select_metric_candidate(
                raw_unit="mW",
                text=text,
            )
        )

        assert (
            selected
            == "output_power"
        ), text


def test_non_output_power_contexts_do_not_select_output_power():

    cases = [
        (
            "The theoretically available "
            "power was 1278 MW."
        ),

        (
            "A total of 116 W of power "
            "is available."
        ),

        (
            "The maximum cooling power "
            "was close to 0.11 W."
        ),

        (
            "The optimized system could "
            "reduce power consumption "
            "to 94 mW."
        ),

        (
            "The laser power was 60 mW."
        ),

        (
            "The input power was 10 W."
        ),

        (
            "The illumination power was "
            "70 mW."
        ),
    ]

    for text in cases:

        selected = (
            select_metric_candidate(
                raw_unit="mW",
                text=text,
            )
        )

        assert (
            selected
            != "output_power"
        ), text


def test_available_power_selects_generic_power():

    selected = (
        select_metric_candidate(
            raw_unit="MW",

            text=(
                "The theoretically available "
                "power reached 1278 MW."
            ),
        )
    )

    assert (
        selected
        == "power"
    )


def test_power_consumption_selects_generic_power():

    selected = (
        select_metric_candidate(
            raw_unit="mW",

            text=(
                "The optimized system "
                "reduced power consumption "
                "to 94 mW."
            ),
        )
    )

    assert (
        selected
        == "power"
    )
