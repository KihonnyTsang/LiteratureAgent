from app.enrichment.provenance_classifier import (
    classify_provenance,
)


def make_row(
    *,
    row_id: int,
    sentence: str,
    context: str | None = None,
) -> dict:

    return {
        "id":
            row_id,

        "sentence_text":
            sentence,

        "context_text":
            (
                sentence
                if context is None
                else context
            ),
    }


def test_author_result_with_first_person_measurement():

    result = classify_provenance(
        make_row(
            row_id=1,

            sentence=(
                "We measured an output "
                "value of 41.02 under "
                "the experimental condition."
            ),
        )
    )

    assert (
        result.status
        == "classified"
    )

    assert (
        result.provenance
        == "author_result"
    )


def test_previous_work_is_cited_literature():

    result = classify_provenance(
        make_row(
            row_id=2,

            sentence=(
                "Previous work reported "
                "a value of 13.5."
            ),
        )
    )

    assert (
        result.status
        == "classified"
    )

    assert (
        result.provenance
        == "cited_literature"
    )


def test_author_name_style_citation_is_cited():

    result = classify_provenance(
        make_row(
            row_id=3,

            sentence=(
                "Smith et al. reported "
                "a value of 10.1."
            ),
        )
    )

    assert (
        result.status
        == "classified"
    )

    assert (
        result.provenance
        == "cited_literature"
    )


def test_neutral_sentence_abstains():

    result = classify_provenance(
        make_row(
            row_id=4,

            sentence=(
                "The measured value "
                "was 8.75."
            ),
        )
    )

    assert (
        result.status
        == "unresolved"
    )

    assert (
        result.provenance
        == "uncertain"
    )


def test_author_result_can_override_weak_literature_reference():

    result = classify_provenance(
        make_row(
            row_id=5,

            sentence=(
                "We have calculated the "
                "maximum value, which is "
                "well agreed with previously "
                "reported literature."
            ),
        )
    )

    assert (
        result.status
        == "classified"
    )

    assert (
        result.provenance
        == "author_result"
    )

def test_proposed_device_alone_does_not_imply_author_result():

    result = classify_provenance(
        make_row(
            row_id=6,

            sentence=(
                "The proposed sensor "
                "exhibited a large response "
                "under applied pressure."
            ),
        )
    )

    assert (
        result.status
        == "unresolved"
    )

    assert (
        result.provenance
        == "uncertain"
    )


def test_according_to_alone_does_not_imply_citation():

    result = classify_provenance(
        make_row(
            row_id=7,

            sentence=(
                "According to the identical "
                "periodic rotation, the "
                "frequency was 5 Hz."
            ),
        )
    )

    assert (
        result.status
        == "unresolved"
    )

    assert (
        result.provenance
        == "uncertain"
    )


def test_according_to_does_not_override_explicit_we_statement():

    result = classify_provenance(
        make_row(
            row_id=8,

            sentence=(
                "According to the stable "
                "output characteristics, "
                "we developed an energy "
                "management circuit."
            ),
        )
    )

    assert (
        result.status
        == "classified"
    )

    assert (
        result.provenance
        == "author_result"
    )


def test_present_work_is_explicit_author_result():

    result = classify_provenance(
        make_row(
            row_id=20,
            sentence=(
                "In the present work, "
                "the device achieved "
                "the reported value."
            ),
        )
    )

    assert result.status == "classified"

    assert (
        result.provenance
        == "author_result"
    )


def test_our_device_is_explicit_author_result():

    result = classify_provenance(
        make_row(
            row_id=21,
            sentence=(
                "Our device generated "
                "the measured output."
            ),
        )
    )

    assert result.status == "classified"

    assert (
        result.provenance
        == "author_result"
    )


def test_this_work_language_alone_abstains():

    result = classify_provenance(
        make_row(
            row_id=22,
            sentence=(
                "This work demonstrates "
                "that the prototype can "
                "produce the reported value."
            ),
        )
    )

    assert (
        result.status
        == "unresolved"
    )

    assert (
        result.provenance
        == "uncertain"
    )


def test_this_study_language_alone_abstains():

    result = classify_provenance(
        make_row(
            row_id=23,
            sentence=(
                "In this study, the "
                "prototype delivered "
                "the maximum value."
            ),
        )
    )

    assert (
        result.status
        == "unresolved"
    )

    assert (
        result.provenance
        == "uncertain"
    )


def test_prototype_language_alone_abstains():

    result = classify_provenance(
        make_row(
            row_id=24,
            sentence=(
                "Under the simulated "
                "excitation, the prototype "
                "delivered a maximum value."
            ),
        )
    )

    assert (
        result.status
        == "unresolved"
    )

    assert (
        result.provenance
        == "uncertain"
    )


def test_generic_review_summary_abstains():

    result = classify_provenance(
        make_row(
            row_id=25,
            sentence=(
                "Generally the power output "
                "from in vivo tests is "
                "under the reported value."
            ),
        )
    )

    assert (
        result.status
        == "unresolved"
    )

    assert (
        result.provenance
        == "uncertain"
    )


def test_et_al_with_numeric_citation_and_investigate_is_cited():

    result = classify_provenance(
        make_row(
            row_id=26,
            sentence=(
                "X. Wang et al. [75] "
                "investigate a standalone "
                "energy-harvesting device."
            ),
        )
    )

    assert (
        result.status
        == "classified"
    )

    assert (
        result.provenance
        == "cited_literature"
    )


def test_external_attribution_in_context_overrides_neutral_sentence():

    result = classify_provenance(
        make_row(
            row_id=27,

            sentence=(
                "As the quantity of units "
                "rises, so does the output, "
                "with the largest measured "
                "value."
            ),

            context=(
                "As the quantity of units "
                "rises, so does the output, "
                "with the largest measured "
                "value. "
                "In this work, X. Wang "
                "et al. [75] investigate "
                "a standalone, completely "
                "encased generator."
            ),
        )
    )

    assert (
        result.status
        == "classified"
    )

    assert (
        result.provenance
        == "cited_literature"
    )


def test_same_sentence_we_achieve_remains_author_result():

    result = classify_provenance(
        make_row(
            row_id=30,
            sentence=(
                "We achieve an output "
                "value of 10 under the "
                "reported condition."
            ),
        )
    )

    assert result.status == "classified"
    assert result.provenance == "author_result"


def test_context_only_we_achieve_does_not_promote_target():

    result = classify_provenance(
        make_row(
            row_id=31,

            sentence=(
                "Generally the power output "
                "from in vivo tests is "
                "under 1 mW."
            ),

            context=(
                "Generally the power output "
                "from in vivo tests is "
                "under 1 mW. "
                "Energy harvesters currently "
                "face complex hurdles and "
                "there is a long way to go "
                "before we achieve "
                "self-powered operation."
            ),
        )
    )

    assert result.status == "unresolved"
    assert result.provenance == "uncertain"


def test_context_we_demonstrated_can_support_target():

    result = classify_provenance(
        make_row(
            row_id=32,

            sentence=(
                "Moreover, the output power "
                "of the hybrid generator "
                "reached 0.31 mW."
            ),

            context=(
                "Moreover, the output power "
                "of the hybrid generator "
                "reached 0.31 mW. "
                "Furthermore, we demonstrated "
                "that the hybrid generator "
                "can power an LED."
            ),
        )
    )

    assert result.status == "classified"
    assert result.provenance == "author_result"
