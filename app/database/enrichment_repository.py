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