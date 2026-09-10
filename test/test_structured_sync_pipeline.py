from unittest.mock import (
    patch,
)

from app.enrichment.metric_classifier import (
    CLASSIFIER_VERSION,
)

from app.enrichment.metric_ontology import (
    ONTOLOGY_VERSION,
)

from app.enrichment.numeric_scanner import (
    DETECTOR_VERSION,
)

from app.enrichment.provenance_classifier import (
    PROVENANCE_CLASSIFIER_VERSION,
)

from app.enrichment.provenance_ontology import (
    PROVENANCE_ONTOLOGY_VERSION,
)

from app.enrichment.sync_pipeline import (
    update_structured_knowledge,
)

from app.enrichment.unit_signature import (
    NORMALIZER_VERSION,
)


def test_structured_sync_pipeline_is_deterministic_and_incremental(
) -> None:

    with (
        patch(
            "app.enrichment.sync_pipeline."
            "update_numeric_mentions",
            return_value={
                "numeric": "ok",
            },
        ) as numeric_update,

        patch(
            "app.enrichment.sync_pipeline."
            "update_unit_signature_cache",
            return_value={
                "units": "ok",
            },
        ) as unit_update,

        patch(
            "app.enrichment.sync_pipeline."
            "update_metric_classification_cache",
            return_value={
                "metrics": "ok",
            },
        ) as metric_update,

        patch(
            "app.enrichment.sync_pipeline."
            "update_provenance_cache",
            return_value={
                "provenance": "ok",
            },
        ) as provenance_update,

        patch(
            "app.enrichment.sync_pipeline."
            "materialize_structured_facts",
            return_value={
                "facts": "ok",
            },
        ) as materialize,
    ):

        result = (
            update_structured_knowledge()
        )

    numeric_update.assert_called_once_with(
        detector_version=(
            DETECTOR_VERSION
        ),
        limit=None,
    )

    unit_update.assert_called_once_with(
        detector_version=(
            DETECTOR_VERSION
        ),
        normalizer_version=(
            NORMALIZER_VERSION
        ),
    )

    metric_update.assert_called_once_with(
        detector_version=(
            DETECTOR_VERSION
        ),
        classifier_version=(
            CLASSIFIER_VERSION
        ),
        ontology_version=(
            ONTOLOGY_VERSION
        ),
        normalizer_version=(
            NORMALIZER_VERSION
        ),
        limit=None,
    )

    provenance_update.assert_called_once_with(
        detector_version=(
            DETECTOR_VERSION
        ),
        metric_classifier_version=(
            CLASSIFIER_VERSION
        ),
        ontology_version=(
            ONTOLOGY_VERSION
        ),
        normalizer_version=(
            NORMALIZER_VERSION
        ),
        provenance_classifier_version=(
            PROVENANCE_CLASSIFIER_VERSION
        ),
        provenance_ontology_version=(
            PROVENANCE_ONTOLOGY_VERSION
        ),
        limit=None,
    )

    materialize.assert_called_once_with()

    assert (
        result[
            "semantic_provenance"
        ][
            "executed"
        ]
        is False
    )


def test_structured_sync_pipeline_does_not_import_semantic_runner(
) -> None:

    import app.enrichment.sync_pipeline as pipeline

    assert not hasattr(
        pipeline,
        "update_semantic_provenance",
    )
