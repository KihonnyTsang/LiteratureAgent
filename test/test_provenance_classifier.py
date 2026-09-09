from app.enrichment.provenance_classifier import (
    classify_provenance,
)


def make_row(
    *,
    row_id: int,
    sentence: str,
) -> dict:

    return {
        "id":
            row_id,

        "sentence_text":
            sentence,

        "context_text":
            sentence,
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