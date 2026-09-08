from pydantic import BaseModel, Field
from typing import Literal


class MetricSpec(BaseModel):
    """
    一个科研指标的定义。
    """

    key: str

    display_name: str

    description: str

    search_queries: list[str]

    canonical_unit: str | None = None

    valid_units: list[str] = Field(
        default_factory=list
    )

    exclude_terms: list[str] = Field(
        default_factory=list
    )


class LLMFact(BaseModel):
    """
    LLM 从论文中抽取的一条科研事实。
    """

    value_type: Literal[
        "scalar",
        "range",
        "lower_bound",
        "upper_bound",
    ] = "scalar"

    value: float | None = None

    value_min: float | None = None
    value_max: float | None = None

    unit: str

    source_id: str

    evidence: str

    condition_text: str | None = None

    provenance: Literal[
        "author_result",
        "cited_literature",
        "uncertain",
    ] = "author_result"

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )


class LLMExtractionResult(BaseModel):
    """
    DeepSeek 一次抽取任务的完整结果。
    """

    found: bool

    facts: list[LLMFact] = Field(
        default_factory=list
    )

    notes: str | None = None


class ExtractedFact(BaseModel):
    """
    Python 完成来源解析后的最终科研事实。
    """

    document_id: str
    metric_name: str

    value_type: Literal[
        "scalar",
        "range",
        "lower_bound",
        "upper_bound",
    ]

    value: float | None = None

    value_min: float | None = None
    value_max: float | None = None

    unit: str

    page_number: int
    chunk_id: int | None = None

    evidence: str
    evidence_verified: bool

    condition_text: str | None = None

    provenance: Literal[
        "author_result",
        "cited_literature",
        "uncertain",
    ]

    confidence: float
