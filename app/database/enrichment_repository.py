import json
import sqlite3
from typing import Any

from app.database.sqlite_db import (
    get_connection,
)


def upsert_document_bibliography(
    document_id: str,
    *,
    doi: str | None = None,
    title: str | None = None,
    authors: list[str] | None = None,
    publication_year: int | None = None,
    journal_name: str | None = None,
    issn: str | None = None,
    eissn: str | None = None,
    volume: str | None = None,
    issue: str | None = None,
    article_pages: str | None = None,
    publisher: str | None = None,
    source: str | None = None,
    metadata_version: str | None = None,
) -> None:
    """
    新增或更新某篇论文的 bibliography enrichment。

    documents 负责 PDF identity。

    document_bibliography 负责可重新获取的
    bibliographic metadata。
    """

    authors_json = json.dumps(
        authors or [],
        ensure_ascii=False,
    )

    connection = get_connection()

    try:

        connection.execute(
            """
            INSERT INTO document_bibliography (
                document_id,
                doi,
                title,
                authors_json,
                publication_year,
                journal_name,
                issn,
                eissn,
                volume,
                issue,
                article_pages,
                publisher,
                source,
                metadata_version
            )

            VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?, ?
            )

            ON CONFLICT(document_id)
            DO UPDATE SET

                doi = excluded.doi,

                title = excluded.title,

                authors_json =
                    excluded.authors_json,

                publication_year =
                    excluded.publication_year,

                journal_name =
                    excluded.journal_name,

                issn = excluded.issn,

                eissn = excluded.eissn,

                volume = excluded.volume,

                issue = excluded.issue,

                article_pages =
                    excluded.article_pages,

                publisher =
                    excluded.publisher,

                source = excluded.source,

                metadata_version =
                    excluded.metadata_version,

                updated_at =
                    CURRENT_TIMESTAMP
            """,
            (
                document_id,
                doi,
                title,
                authors_json,
                publication_year,
                journal_name,
                issn,
                eissn,
                volume,
                issue,
                article_pages,
                publisher,
                source,
                metadata_version,
            ),
        )

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def get_document_bibliography(
    document_id: str,
) -> dict[str, Any] | None:
    """
    获取一篇论文的 bibliography。
    """

    connection = get_connection()

    connection.row_factory = (
        sqlite3.Row
    )

    try:

        cursor = connection.execute(
            """
            SELECT *
            FROM document_bibliography
            WHERE document_id = ?
            LIMIT 1
            """,
            (
                document_id,
            ),
        )

        row = cursor.fetchone()

        if row is None:

            return None

        result = dict(
            row
        )

        try:

            result["authors"] = (
                json.loads(
                    result.get(
                        "authors_json"
                    )
                    or "[]"
                )
            )

        except json.JSONDecodeError:

            result["authors"] = []

        return result

    finally:

        connection.close()


def upsert_journal_metric(
    *,
    journal_key: str,
    metric_key: str,
    source: str,
    metric_year: int = 0,
    journal_name: str | None = None,
    issn: str | None = None,
    eissn: str | None = None,
    metric_value_text: str | None = None,
    metric_value_number: float | None = None,
    raw_payload: dict | None = None,
) -> None:
    """
    新增或更新一个 Journal Metric。

    journal_key 应由 enrichment layer
    根据稳定 journal identity 构造。

    优先级以后建议：

        ISSN
        > eISSN
        > normalized journal name
    """

    raw_payload_json = None

    if raw_payload is not None:

        raw_payload_json = json.dumps(
            raw_payload,
            ensure_ascii=False,
        )

    connection = get_connection()

    try:

        connection.execute(
            """
            INSERT INTO journal_metrics (
                journal_key,
                journal_name,
                issn,
                eissn,
                metric_key,
                metric_value_text,
                metric_value_number,
                metric_year,
                source,
                raw_payload_json
            )

            VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?
            )

            ON CONFLICT(
                journal_key,
                metric_key,
                metric_year,
                source
            )

            DO UPDATE SET

                journal_name =
                    excluded.journal_name,

                issn = excluded.issn,

                eissn = excluded.eissn,

                metric_value_text =
                    excluded.metric_value_text,

                metric_value_number =
                    excluded.metric_value_number,

                raw_payload_json =
                    excluded.raw_payload_json,

                retrieved_at =
                    CURRENT_TIMESTAMP
            """,
            (
                journal_key,
                journal_name,
                issn,
                eissn,
                metric_key,
                metric_value_text,
                metric_value_number,
                metric_year,
                source,
                raw_payload_json,
            ),
        )

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def get_journal_metrics(
    journal_key: str,
) -> list[dict[str, Any]]:
    """
    获取某个 journal 的全部 metrics。
    """

    connection = get_connection()

    connection.row_factory = (
        sqlite3.Row
    )

    try:

        cursor = connection.execute(
            """
            SELECT *
            FROM journal_metrics
            WHERE journal_key = ?
            ORDER BY
                metric_year DESC,
                metric_key
            """,
            (
                journal_key,
            ),
        )

        return [
            dict(row)
            for row
            in cursor.fetchall()
        ]

    finally:

        connection.close()


def replace_numeric_mentions_for_document(
    document_id: str,
    detector_version: str,
    mentions: list[dict],
) -> None:
    """
    原子替换某篇文档某一 detector version
    产生的全部 Numeric Mentions。

    这个设计允许 scanner 升级版本后重新生成，
    而不会和旧版本结果混在一起。
    """

    connection = get_connection()

    try:

        connection.execute(
            """
            DELETE FROM numeric_mentions

            WHERE document_id = ?
              AND detector_version = ?
            """,
            (
                document_id,
                detector_version,
            ),
        )

        records = []

        for mention in mentions:

            records.append(
                (
                    document_id,

                    mention[
                        "page_number"
                    ],

                    mention.get(
                        "source_chunk_id"
                    ),

                    mention[
                        "mention_key"
                    ],

                    mention[
                        "raw_text"
                    ],

                    mention.get(
                        "value_type",
                        "scalar",
                    ),

                    mention.get(
                        "raw_value"
                    ),

                    mention.get(
                        "raw_value_min"
                    ),

                    mention.get(
                        "raw_value_max"
                    ),

                    mention.get(
                        "raw_unit"
                    ),

                    mention.get(
                        "sentence_text"
                    ),

                    mention.get(
                        "context_text"
                    ),

                    detector_version,
                )
            )

        if records:

            connection.executemany(
                """
                INSERT INTO numeric_mentions (
                    document_id,
                    page_number,
                    source_chunk_id,
                    mention_key,
                    raw_text,
                    value_type,
                    raw_value,
                    raw_value_min,
                    raw_value_max,
                    raw_unit,
                    sentence_text,
                    context_text,
                    detector_version
                )

                VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?
                )
                """,
                records,
            )

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def get_numeric_mentions(
    *,
    document_id: str | None = None,
    raw_unit: str | None = None,
    detector_version: str | None = None,
) -> list[dict[str, Any]]:
    """
    查询已生成的 Numeric Mentions。
    """

    connection = get_connection()

    connection.row_factory = (
        sqlite3.Row
    )

    try:

        sql = """
        SELECT *
        FROM numeric_mentions
        WHERE 1 = 1
        """

        parameters = []

        if document_id is not None:

            sql += """
            AND document_id = ?
            """

            parameters.append(
                document_id
            )

        if raw_unit is not None:

            sql += """
            AND raw_unit = ?
            """

            parameters.append(
                raw_unit
            )

        if detector_version is not None:

            sql += """
            AND detector_version = ?
            """

            parameters.append(
                detector_version
            )

        sql += """
        ORDER BY
            document_id,
            page_number,
            id
        """

        cursor = connection.execute(
            sql,
            parameters,
        )

        return [
            dict(row)
            for row
            in cursor.fetchall()
        ]

    finally:

        connection.close()

def has_current_numeric_scan(
    *,
    document_id: str,
    content_hash: str,
    detector_version: str,
) -> bool:
    """
    判断当前 PDF 内容是否已经被指定版本
    Numeric Scanner 成功扫描。

    MOVED：
        content_hash 不变
        -> True

    MODIFIED：
        content_hash 改变
        -> False
    """

    connection = get_connection()

    try:

        cursor = connection.execute(
            """
            SELECT 1

            FROM numeric_scan_runs

            WHERE document_id = ?
              AND detector_version = ?
              AND content_hash = ?
              AND status = 'success'

            LIMIT 1
            """,
            (
                document_id,
                detector_version,
                content_hash,
            ),
        )

        return (
            cursor.fetchone()
            is not None
        )

    finally:

        connection.close()


def replace_numeric_scan_result(
    *,
    document_id: str,
    content_hash: str,
    detector_version: str,
    mentions: list[dict],
) -> None:
    """
    原子保存一次完整 Numeric Scan。

    同一个事务内：

    1. 删除该 detector version 的旧 mentions
    2. 写入新的 mentions
    3. 更新 numeric_scan_runs

    即使 mentions == []，
    也记录 success + mention_count = 0。
    """

    connection = get_connection()

    try:

        connection.execute(
            """
            DELETE FROM numeric_mentions

            WHERE document_id = ?
              AND detector_version = ?
            """,
            (
                document_id,
                detector_version,
            ),
        )

        records = []

        for mention in mentions:

            records.append(
                (
                    document_id,

                    mention[
                        "page_number"
                    ],

                    mention.get(
                        "source_chunk_id"
                    ),

                    mention[
                        "mention_key"
                    ],

                    mention[
                        "raw_text"
                    ],

                    mention.get(
                        "value_type",
                        "scalar",
                    ),

                    mention.get(
                        "raw_value"
                    ),

                    mention.get(
                        "raw_value_min"
                    ),

                    mention.get(
                        "raw_value_max"
                    ),

                    mention.get(
                        "raw_unit"
                    ),

                    mention.get(
                        "sentence_text"
                    ),

                    mention.get(
                        "context_text"
                    ),

                    detector_version,
                )
            )

        if records:

            connection.executemany(
                """
                INSERT INTO numeric_mentions (
                    document_id,
                    page_number,
                    source_chunk_id,
                    mention_key,
                    raw_text,
                    value_type,
                    raw_value,
                    raw_value_min,
                    raw_value_max,
                    raw_unit,
                    sentence_text,
                    context_text,
                    detector_version
                )

                VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?
                )
                """,
                records,
            )

        connection.execute(
            """
            INSERT INTO numeric_scan_runs (
                document_id,
                detector_version,
                content_hash,
                status,
                mention_count
            )

            VALUES (
                ?, ?, ?, 'success', ?
            )

            ON CONFLICT(
                document_id,
                detector_version
            )

            DO UPDATE SET

                content_hash =
                    excluded.content_hash,

                status =
                    'success',

                mention_count =
                    excluded.mention_count,

                updated_at =
                    CURRENT_TIMESTAMP
            """,
            (
                document_id,
                detector_version,
                content_hash,
                len(mentions),
            ),
        )

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()

def get_distinct_numeric_units(
    *,
    detector_version: str,
) -> list[str]:
    """
    获取某个 Numeric Scanner version
    已发现的全部 raw units。
    """

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT DISTINCT raw_unit

            FROM numeric_mentions

            WHERE detector_version = ?
              AND raw_unit IS NOT NULL
              AND TRIM(raw_unit) != ''

            ORDER BY raw_unit
            """,
            (
                detector_version,
            ),
        ).fetchall()

        return [
            row[0]
            for row in rows
        ]

    finally:

        connection.close()


def get_current_unit_signature_units(
    *,
    normalizer_version: str,
) -> set[str]:
    """
    获取已经由当前 normalizer version
    完成解析的 raw units。
    """

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT raw_unit

            FROM unit_signatures

            WHERE normalizer_version = ?
            """,
            (
                normalizer_version,
            ),
        ).fetchall()

        return {
            row[0]
            for row in rows
        }

    finally:

        connection.close()


def upsert_unit_signatures(
    signatures: list[dict],
) -> None:
    """
    批量保存 Unit Signatures。
    """

    if not signatures:

        return

    connection = get_connection()

    try:

        records = [
            (
                item[
                    "raw_unit"
                ],

                item[
                    "normalized_unit_text"
                ],

                item[
                    "parse_status"
                ],

                item.get(
                    "dimensionality"
                ),

                item.get(
                    "base_unit"
                ),

                item.get(
                    "scale_to_base"
                ),

                item.get(
                    "parse_error"
                ),

                item[
                    "normalizer_version"
                ],
            )
            for item
            in signatures
        ]

        connection.executemany(
            """
            INSERT INTO unit_signatures (
                raw_unit,
                normalized_unit_text,
                parse_status,
                dimensionality,
                base_unit,
                scale_to_base,
                parse_error,
                normalizer_version
            )

            VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?
            )

            ON CONFLICT(raw_unit)
            DO UPDATE SET

                normalized_unit_text =
                    excluded.normalized_unit_text,

                parse_status =
                    excluded.parse_status,

                dimensionality =
                    excluded.dimensionality,

                base_unit =
                    excluded.base_unit,

                scale_to_base =
                    excluded.scale_to_base,

                parse_error =
                    excluded.parse_error,

                normalizer_version =
                    excluded.normalizer_version,

                updated_at =
                    CURRENT_TIMESTAMP
            """,
            records,
        )

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def get_unit_signature_rows(
    *,
    normalizer_version: str | None = None,
) -> list[dict]:
    """
    获取 Unit Signature vocabulary。
    """

    connection = get_connection()

    connection.row_factory = (
        sqlite3.Row
    )

    try:

        sql = """
        SELECT *
        FROM unit_signatures
        WHERE 1 = 1
        """

        parameters = []

        if normalizer_version is not None:

            sql += """
            AND normalizer_version = ?
            """

            parameters.append(
                normalizer_version
            )

        sql += """
        ORDER BY raw_unit
        """

        rows = connection.execute(
            sql,
            parameters,
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        connection.close()

def get_current_metric_classification_mention_ids(
    *,
    detector_version: str,
    classifier_version: str,
    ontology_version: str,
    normalizer_version: str,
) -> set[int]:
    """
    获取当前 Numeric Mention vocabulary 中，
    已完成指定 classification version 的 mention ids。
    """

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT
                nmc.mention_id

            FROM numeric_metric_classifications
                AS nmc

            JOIN numeric_mentions AS nm
              ON nm.id = nmc.mention_id

            WHERE nm.detector_version = ?
              AND nmc.classifier_version = ?
              AND nmc.ontology_version = ?
              AND nmc.normalizer_version = ?
            """,
            (
                detector_version,
                classifier_version,
                ontology_version,
                normalizer_version,
            ),
        ).fetchall()

        return {
            int(row[0])
            for row in rows
        }

    finally:

        connection.close()


def upsert_metric_classifications(
    classifications: list[dict],
) -> None:
    """
    批量保存 Metric Classification cache。
    """

    if not classifications:

        return

    connection = get_connection()

    try:

        records = [
            (
                item["mention_id"],
                item["classifier_version"],
                item["ontology_version"],
                item["normalizer_version"],
                item["status"],
                item.get("metric_key"),
                item.get(
                    "method",
                    "deterministic",
                ),
                item.get("score"),
                item.get(
                    "candidates_json",
                    "[]",
                ),
                item.get("reason"),
            )
            for item
            in classifications
        ]

        connection.executemany(
            """
            INSERT INTO
                numeric_metric_classifications (
                    mention_id,
                    classifier_version,
                    ontology_version,
                    normalizer_version,
                    status,
                    metric_key,
                    method,
                    score,
                    candidates_json,
                    reason
                )

            VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?
            )

            ON CONFLICT(
                mention_id,
                classifier_version,
                ontology_version,
                normalizer_version
            )

            DO UPDATE SET

                status =
                    excluded.status,

                metric_key =
                    excluded.metric_key,

                method =
                    excluded.method,

                score =
                    excluded.score,

                candidates_json =
                    excluded.candidates_json,

                reason =
                    excluded.reason,

                updated_at =
                    CURRENT_TIMESTAMP
            """,
            records,
        )

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def get_metric_classification_rows(
    *,
    detector_version: str | None = None,
    classifier_version: str | None = None,
    ontology_version: str | None = None,
    normalizer_version: str | None = None,
    status: str | None = None,
    metric_key: str | None = None,
) -> list[dict]:
    """
    查询 Metric Classification cache。

    返回 classification，同时附带对应
    Numeric Mention 的基本 provenance。
    """

    connection = get_connection()

    connection.row_factory = (
        sqlite3.Row
    )

    try:

        sql = """
        SELECT
            nmc.*,

            nm.document_id
                AS document_id,

            nm.detector_version
                AS detector_version,

            nm.page_number
                AS page_number,

            nm.raw_value
                AS raw_value,

            nm.raw_unit
                AS raw_unit

        FROM numeric_metric_classifications
            AS nmc

        JOIN numeric_mentions AS nm
          ON nm.id = nmc.mention_id

        WHERE 1 = 1
        """

        parameters = []

        if detector_version is not None:

            sql += """
            AND nm.detector_version = ?
            """

            parameters.append(
                detector_version
            )

        if classifier_version is not None:

            sql += """
            AND nmc.classifier_version = ?
            """

            parameters.append(
                classifier_version
            )

        if ontology_version is not None:

            sql += """
            AND nmc.ontology_version = ?
            """

            parameters.append(
                ontology_version
            )

        if normalizer_version is not None:

            sql += """
            AND nmc.normalizer_version = ?
            """

            parameters.append(
                normalizer_version
            )

        if status is not None:

            sql += """
            AND nmc.status = ?
            """

            parameters.append(
                status
            )

        if metric_key is not None:

            sql += """
            AND nmc.metric_key = ?
            """

            parameters.append(
                metric_key
            )

        sql += """
        ORDER BY
            nm.document_id,
            nm.page_number,
            nmc.mention_id
        """

        rows = connection.execute(
            sql,
            parameters,
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        connection.close()

def get_current_provenance_metric_classification_ids(
    *,
    detector_version: str,
    metric_classifier_version: str,
    ontology_version: str,
    normalizer_version: str,
    provenance_classifier_version: str,
    provenance_ontology_version: str,
) -> set[int]:

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT
                npc.metric_classification_id

            FROM numeric_provenance_classifications
                AS npc

            JOIN numeric_metric_classifications
                AS nmc
              ON nmc.id =
                 npc.metric_classification_id

            JOIN numeric_mentions
                AS nm
              ON nm.id =
                 nmc.mention_id

            WHERE nm.detector_version = ?

              AND nmc.classifier_version = ?
              AND nmc.ontology_version = ?
              AND nmc.normalizer_version = ?
              AND nmc.status = 'classified'

              AND
                npc.provenance_classifier_version = ?

              AND
                npc.provenance_ontology_version = ?
            """,
            (
                detector_version,
                metric_classifier_version,
                ontology_version,
                normalizer_version,
                provenance_classifier_version,
                provenance_ontology_version,
            ),
        ).fetchall()

        return {
            int(row[0])
            for row in rows
        }

    finally:

        connection.close()


def upsert_provenance_classifications(
    classifications: list[dict],
) -> None:

    if not classifications:

        return

    connection = get_connection()

    try:

        records = [
            (
                item[
                    "metric_classification_id"
                ],

                item[
                    "provenance_classifier_version"
                ],

                item[
                    "provenance_ontology_version"
                ],

                item["status"],

                item["provenance"],

                item.get(
                    "method",
                    "deterministic",
                ),

                item.get("score"),

                item.get(
                    "candidates_json",
                    "[]",
                ),

                item.get("reason"),
            )
            for item
            in classifications
        ]

        connection.executemany(
            """
            INSERT INTO
                numeric_provenance_classifications (
                    metric_classification_id,
                    provenance_classifier_version,
                    provenance_ontology_version,
                    status,
                    provenance,
                    method,
                    score,
                    candidates_json,
                    reason
                )

            VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?
            )

            ON CONFLICT(
                metric_classification_id,
                provenance_classifier_version,
                provenance_ontology_version
            )

            DO UPDATE SET

                status =
                    excluded.status,

                provenance =
                    excluded.provenance,

                method =
                    excluded.method,

                score =
                    excluded.score,

                candidates_json =
                    excluded.candidates_json,

                reason =
                    excluded.reason,

                updated_at =
                    CURRENT_TIMESTAMP
            """,
            records,
        )

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def get_provenance_classification_rows(
    *,
    detector_version: str | None = None,
    metric_classifier_version: str | None = None,
    ontology_version: str | None = None,
    normalizer_version: str | None = None,
    provenance_classifier_version: str | None = None,
    provenance_ontology_version: str | None = None,
    status: str | None = None,
    provenance: str | None = None,
) -> list[dict]:

    connection = get_connection()

    connection.row_factory = (
        sqlite3.Row
    )

    try:

        sql = """
        SELECT
            npc.*,

            nmc.metric_key
                AS metric_key,

            nmc.classifier_version
                AS metric_classifier_version,

            nmc.ontology_version
                AS ontology_version,

            nmc.normalizer_version
                AS normalizer_version,

            nm.id
                AS mention_id,

            nm.document_id
                AS document_id,

            nm.detector_version
                AS detector_version,

            nm.page_number
                AS page_number,

            nm.raw_text
                AS raw_text,

            nm.raw_value
                AS raw_value,

            nm.raw_unit
                AS raw_unit,

            nm.sentence_text
                AS sentence_text,

            nm.context_text
                AS context_text

        FROM numeric_provenance_classifications
            AS npc

        JOIN numeric_metric_classifications
            AS nmc
          ON nmc.id =
             npc.metric_classification_id

        JOIN numeric_mentions AS nm
          ON nm.id =
             nmc.mention_id

        WHERE 1 = 1
        """

        parameters = []

        if detector_version is not None:

            sql += """
            AND nm.detector_version = ?
            """

            parameters.append(
                detector_version
            )

        if metric_classifier_version is not None:

            sql += """
            AND nmc.classifier_version = ?
            """

            parameters.append(
                metric_classifier_version
            )

        if ontology_version is not None:

            sql += """
            AND nmc.ontology_version = ?
            """

            parameters.append(
                ontology_version
            )

        if normalizer_version is not None:

            sql += """
            AND nmc.normalizer_version = ?
            """

            parameters.append(
                normalizer_version
            )

        if provenance_classifier_version is not None:

            sql += """
            AND
                npc.provenance_classifier_version = ?
            """

            parameters.append(
                provenance_classifier_version
            )

        if provenance_ontology_version is not None:

            sql += """
            AND
                npc.provenance_ontology_version = ?
            """

            parameters.append(
                provenance_ontology_version
            )

        if status is not None:

            sql += """
            AND npc.status = ?
            """

            parameters.append(
                status
            )

        if provenance is not None:

            sql += """
            AND npc.provenance = ?
            """

            parameters.append(
                provenance
            )

        sql += """
        ORDER BY
            nm.document_id,
            nm.page_number,
            nm.id
        """

        rows = connection.execute(
            sql,
            parameters,
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        connection.close()

def get_pending_provenance_input_rows(
    *,
    detector_version: str,
    metric_classifier_version: str,
    ontology_version: str,
    normalizer_version: str,
    provenance_classifier_version: str,
    provenance_ontology_version: str,
) -> list[dict]:

    connection = get_connection()

    connection.row_factory = (
        sqlite3.Row
    )

    try:

        rows = connection.execute(
            """
            SELECT
                nmc.id
                    AS id,

                nmc.metric_key
                    AS metric_key,

                nm.id
                    AS mention_id,

                nm.document_id
                    AS document_id,

                nm.page_number
                    AS page_number,

                nm.mention_key
                    AS mention_key,

                nm.raw_text
                    AS raw_text,

                nm.raw_value
                    AS raw_value,

                nm.raw_unit
                    AS raw_unit,

                nm.sentence_text
                    AS sentence_text,

                nm.context_text
                    AS context_text

            FROM numeric_metric_classifications
                AS nmc

            JOIN numeric_mentions AS nm
              ON nm.id = nmc.mention_id

            LEFT JOIN
                numeric_provenance_classifications
                AS npc

              ON npc.metric_classification_id =
                    nmc.id

             AND npc.provenance_classifier_version = ?

             AND npc.provenance_ontology_version = ?

            WHERE nm.detector_version = ?

              AND nmc.classifier_version = ?
              AND nmc.ontology_version = ?
              AND nmc.normalizer_version = ?
              AND nmc.status = 'classified'

              AND npc.id IS NULL

            ORDER BY
                nm.document_id,
                nm.page_number,
                nm.id
            """,
            (
                provenance_classifier_version,
                provenance_ontology_version,
                detector_version,
                metric_classifier_version,
                ontology_version,
                normalizer_version,
            ),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        connection.close()

def get_pending_semantic_provenance_input_rows(
    *,
    detector_version: str,
    metric_classifier_version: str,
    metric_ontology_version: str,
    normalizer_version: str,
    deterministic_classifier_version: str,
    provenance_ontology_version: str,
    semantic_classifier_version: str,
) -> list[dict]:

    connection = get_connection()

    connection.row_factory = (
        sqlite3.Row
    )

    try:

        rows = connection.execute(
            """
            SELECT
                nmc.id
                    AS id,

                nmc.metric_key
                    AS metric_key,

                nm.id
                    AS mention_id,

                nm.document_id
                    AS document_id,

                nm.page_number
                    AS page_number,

                nm.mention_key
                    AS mention_key,

                nm.raw_text
                    AS raw_text,

                nm.raw_value
                    AS raw_value,

                nm.raw_unit
                    AS raw_unit,

                nm.sentence_text
                    AS sentence_text,

                nm.context_text
                    AS context_text

            FROM numeric_metric_classifications
                AS nmc

            JOIN numeric_mentions AS nm
              ON nm.id =
                 nmc.mention_id

            JOIN numeric_provenance_classifications
                AS deterministic

              ON deterministic.metric_classification_id =
                    nmc.id

             AND deterministic.provenance_classifier_version = ?

             AND deterministic.provenance_ontology_version = ?

            LEFT JOIN numeric_provenance_classifications
                AS semantic

              ON semantic.metric_classification_id =
                    nmc.id

             AND semantic.provenance_classifier_version = ?

             AND semantic.provenance_ontology_version = ?

            WHERE nm.detector_version = ?

              AND nmc.classifier_version = ?

              AND nmc.ontology_version = ?

              AND nmc.normalizer_version = ?

              AND nmc.status = 'classified'

              AND deterministic.status = 'unresolved'

              AND semantic.id IS NULL

            ORDER BY
                nm.document_id,
                nm.page_number,
                nm.id
            """,
            (
                deterministic_classifier_version,
                provenance_ontology_version,

                semantic_classifier_version,
                provenance_ontology_version,

                detector_version,
                metric_classifier_version,
                metric_ontology_version,
                normalizer_version,
            ),
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:

        connection.close()