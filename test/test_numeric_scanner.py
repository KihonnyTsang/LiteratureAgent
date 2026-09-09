from app.enrichment.numeric_scanner import (
    scan_page_numeric_mentions,
)


def test_scanner_extracts_scalar_units():

    text = (
        "The maximum output power density "
        "was 41.02 μW/cm² under a force "
        "of 5 N."
    )

    mentions = (
        scan_page_numeric_mentions(
            page_number=7,
            text=text,
        )
    )

    values = {
        item.raw_text:
            item
        for item in mentions
    }

    assert (
        "41.02 μW/cm²"
        in values
    )

    assert (
        values[
            "41.02 μW/cm²"
        ].raw_value
        == 41.02
    )

    assert (
        values[
            "41.02 μW/cm²"
        ].raw_unit
        == "μW/cm²"
    )

    assert (
        "5 N"
        in values
    )


def test_scanner_extracts_unicode_compound_units():

    text = (
        "An energy density of "
        "14.2 J/cm³ was obtained, "
        "while the electric field "
        "reached 320 kV/mm."
    )

    mentions = (
        scan_page_numeric_mentions(
            page_number=3,
            text=text,
        )
    )

    raw_texts = {
        item.raw_text
        for item in mentions
    }

    assert (
        "14.2 J/cm³"
        in raw_texts
    )

    assert (
        "320 kV/mm"
        in raw_texts
    )


def test_scanner_extracts_range_once():

    text = (
        "The device operated from "
        "10-20 kV/mm."
    )

    mentions = (
        scan_page_numeric_mentions(
            page_number=2,
            text=text,
        )
    )

    assert len(mentions) == 1

    mention = mentions[0]

    assert (
        mention.value_type
        == "range"
    )

    assert (
        mention.raw_value_min
        == 10.0
    )

    assert (
        mention.raw_value_max
        == 20.0
    )

    assert (
        mention.raw_unit
        == "kV/mm"
    )


def test_scanner_ignores_bare_numbers():

    text = (
        "Figure 3 shows results "
        "reported in 2018 for "
        "sample 5."
    )

    mentions = (
        scan_page_numeric_mentions(
            page_number=1,
            text=text,
        )
    )

    assert mentions == []


def test_scanner_preserves_evidence_context():

    text = (
        "The sample was tested. "
        "The maximum output voltage "
        "was 35 V under cyclic loading. "
        "The device remained stable."
    )

    mentions = (
        scan_page_numeric_mentions(
            page_number=5,
            text=text,
        )
    )

    assert len(mentions) == 1

    mention = mentions[0]

    assert (
        "maximum output voltage"
        in mention.sentence_text
    )

    assert (
        "35 V"
        in mention.context_text
    )

    assert (
        mention.page_number
        == 5
    )

def test_scanner_does_not_consume_normal_words_as_units():

    text = (
        "The value was 41.02 μW/cm² "
        "under loading, and the study "
        "was reported in 2018 for "
        "sample 5."
    )

    mentions = (
        scan_page_numeric_mentions(
            page_number=1,
            text=text,
        )
    )

    raw_texts = [
        item.raw_text
        for item in mentions
    ]

    assert raw_texts == [
        "41.02 μW/cm²"
    ]

def test_scanner_keeps_real_seconds_unit():

    text = (
        "The loading duration was "
        "3 s under constant force."
    )

    mentions = (
        scan_page_numeric_mentions(
            page_number=1,
            text=text,
        )
    )

    assert len(mentions) == 1

    mention = mentions[0]

    assert (
        mention.raw_text
        == "3 s"
    )

    assert (
        mention.raw_value
        == 3.0
    )

    assert (
        mention.raw_unit
        == "s"
    )

def test_scanner_rejects_figure_panel_labels():

    text = (
        "Figure 2C explains the mechanism. "
        "The result is shown in Figure 5g."
    )

    mentions = (
        scan_page_numeric_mentions(
            page_number=3,
            text=text,
        )
    )

    assert mentions == []


def test_scanner_extracts_spaced_composition_percent():

    text = (
        "The ZnO mass fraction increased "
        "from 10 wt % to 60 wt %."
    )

    mentions = (
        scan_page_numeric_mentions(
            page_number=5,
            text=text,
        )
    )

    raw_texts = {
        item.raw_text
        for item in mentions
    }

    assert (
        "10 wt %"
        in raw_texts
    )

    assert (
        "60 wt %"
        in raw_texts
    )


def test_sentence_extractor_ignores_decimal_points():

    text = (
        "The open-circuit voltage was "
        "84.5 V, and the peak output power "
        "was 0.46 mW under loading."
    )

    mentions = (
        scan_page_numeric_mentions(
            page_number=1,
            text=text,
        )
    )

    power_mention = next(
        item
        for item in mentions
        if item.raw_text
        == "0.46 mW"
    )

    assert (
        "84.5 V"
        in power_mention.sentence_text
    )

    assert (
        "0.46 mW"
        in power_mention.sentence_text
    )