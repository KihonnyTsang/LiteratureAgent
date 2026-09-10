from typing import Any

from app.enrichment.fact_materializer import (
    materialize_structured_facts,
)

from app.enrichment.metric_classifier import (
    CLASSIFIER_VERSION,
)

from app.enrichment.metric_ontology import (
    ONTOLOGY_VERSION,
)

from app.enrichment.numeric_scanner import (
    DETECTOR_VERSION,
    update_numeric_mentions,
)

from app.enrichment.provenance_classifier import (
    PROVENANCE_CLASSIFIER_VERSION,
)

from app.enrichment.provenance_ontology import (
    PROVENANCE_ONTOLOGY_VERSION,
)

from app.enrichment.unit_signature import (
    NORMALIZER_VERSION,
)

from update_metric_classifications import (
    update_metric_classification_cache,
)

from update_provenance_classifications import (
    update_provenance_cache,
)

from update_unit_signatures import (
    update_unit_signature_cache,
)


def update_structured_knowledge(
) -> dict[str, Any]:
    """
    Incrementally refresh deterministic structured knowledge.

    Pipeline:

    numeric mentions
    -> unit signatures
    -> metric classifications
    -> deterministic provenance
    -> materialized facts

    Existing cache contracts decide what is pending, so unchanged
    documents and already-classified mentions are not recomputed.

    Semantic provenance is intentionally NOT executed here.
    No LLM call is made by this pipeline.
    """

    numeric_result = (
        update_numeric_mentions(
            detector_version=(
                DETECTOR_VERSION
            ),
            limit=None,
        )
    )

    unit_result = (
        update_unit_signature_cache(
            detector_version=(
                DETECTOR_VERSION
            ),
            normalizer_version=(
                NORMALIZER_VERSION
            ),
        )
    )

    metric_result = (
        update_metric_classification_cache(
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
    )

    provenance_result = (
        update_provenance_cache(
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
    )

    materialization_result = (
        materialize_structured_facts()
    )

    return {
        "numeric":
            numeric_result,

        "unit_signatures":
            unit_result,

        "metric_classifications":
            metric_result,

        "deterministic_provenance":
            provenance_result,

        "materialized_facts":
            materialization_result,

        "semantic_provenance":
            {
                "executed": False,
                "reason": (
                    "not part of deterministic "
                    "knowledge-base sync"
                ),
            },
    }
