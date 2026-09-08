from app.database.sqlite_db import (
    get_connection,
)

from app.extraction.schemas import (
    ExtractedFact,
    MetricSpec,
)

from app.extraction.unit_normalizer import (
    normalize_fact,
)


# ============================================================
# Facts 表结构
# ============================================================

FACT_COLUMNS = {

    "value_type":
        "TEXT NOT NULL DEFAULT 'scalar'",

    "raw_value":
        "REAL",

    "raw_value_min":
        "REAL",

    "raw_value_max":
        "REAL",

    "raw_unit":
        "TEXT",

    "normalized_value":
        "REAL",

    "normalized_value_min":
        "REAL",

    "normalized_value_max":
        "REAL",

    "normalized_unit":
        "TEXT",

    "normalization_converted":
        "INTEGER NOT NULL DEFAULT 0",

    "normalization_error":
        "TEXT",

    "page_number":
        "INTEGER",

    "source_chunk_id":
        "INTEGER",

    "evidence":
        "TEXT",

    "evidence_verified":
        "INTEGER NOT NULL DEFAULT 0",

    "condition_text":
        "TEXT",

    "provenance":
        "TEXT NOT NULL DEFAULT 'author_result'",

    "confidence":
        "REAL",

    "extraction_scope":
        "TEXT NOT NULL DEFAULT 'author_results'",

    "extraction_version":
        "TEXT NOT NULL DEFAULT 'v1'",
}


def get_table_columns(
    connection,
    table_name: str,
) -> set[str]:
    """
    获取 SQLite 表中已有的字段名。
    """

    cursor = connection.execute(
        f"PRAGMA table_info({table_name})"
    )

    return {
        row[1]
        for row in cursor.fetchall()
    }


def ensure_facts_schema():
    """
    创建或升级 facts 表。

    之所以需要 migration：
    之前项目里已经创建过旧版 facts 表，
    CREATE TABLE IF NOT EXISTS 不会自动增加新字段。
    """

    connection = get_connection()

    try:

        # ----------------------------------------------------
        # 如果 facts 表不存在，创建完整新版
        # ----------------------------------------------------

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS facts (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                document_id TEXT NOT NULL,

                metric_name TEXT NOT NULL,

                value_type TEXT NOT NULL DEFAULT 'scalar',

                raw_value REAL,
                raw_value_min REAL,
                raw_value_max REAL,
                raw_unit TEXT,

                normalized_value REAL,
                normalized_value_min REAL,
                normalized_value_max REAL,
                normalized_unit TEXT,

                normalization_converted
                    INTEGER NOT NULL DEFAULT 0,

                normalization_error TEXT,

                page_number INTEGER,
                source_chunk_id INTEGER,

                evidence TEXT,

                evidence_verified
                    INTEGER NOT NULL DEFAULT 0,

                condition_text TEXT,

                provenance
                    TEXT NOT NULL
                    DEFAULT 'author_result',

                confidence REAL,

                extraction_scope
                    TEXT NOT NULL
                    DEFAULT 'author_results',

                extraction_version
                    TEXT NOT NULL
                    DEFAULT 'v1',

                created_at
                    TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (document_id)
                    REFERENCES documents(id)
            )
            """
        )

        # ----------------------------------------------------
        # 如果是旧版 facts 表：
        # 自动补充缺失字段
        # ----------------------------------------------------

        existing_columns = get_table_columns(
            connection,
            "facts",
        )

        for (
            column_name,
            column_definition,
        ) in FACT_COLUMNS.items():

            if (
                column_name
                not in existing_columns
            ):

                print(
                    f"升级 facts 表："
                    f"新增字段 {column_name}"
                )

                connection.execute(
                    f"""
                    ALTER TABLE facts
                    ADD COLUMN
                    {column_name}
                    {column_definition}
                    """
                )

        # ----------------------------------------------------
        # 常用查询索引
        # ----------------------------------------------------

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_facts_document_metric

            ON facts(
                document_id,
                metric_name
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_facts_metric_provenance

            ON facts(
                metric_name,
                provenance
            )
            """
        )
        # ----------------------------------------------------
        # Extraction Runs
        #
        # 用来记录：
        # 某篇论文 + 某指标 + 某抽取范围
        # 是否已经成功检查过。
        #
        # 即使 fact_count = 0，
        # 也表示这是一个有效的缓存结果。
        # ----------------------------------------------------

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS extraction_runs (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                document_id TEXT NOT NULL,

                metric_name TEXT NOT NULL,

                extraction_scope TEXT NOT NULL,

                extraction_version TEXT NOT NULL,

                status TEXT NOT NULL
                    DEFAULT 'success',

                fact_count INTEGER NOT NULL
                    DEFAULT 0,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                UNIQUE (
                    document_id,
                    metric_name,
                    extraction_scope,
                    extraction_version
                ),

                FOREIGN KEY (document_id)
                    REFERENCES documents(id)
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_extraction_runs_lookup

            ON extraction_runs(
                document_id,
                metric_name,
                extraction_scope,
                extraction_version
            )
            """
        )

        connection.commit()

    finally:

        connection.close()


def replace_facts_for_document_metric(
    document_id: str,
    metric_spec: MetricSpec,
    facts: list[ExtractedFact],
    provenance_scope: str,
    extraction_version: str = "v1",
):
    """
    保存某篇论文某个科研指标的抽取结果。

    唯一任务由以下四项共同确定：

    document_id
    metric_name
    provenance_scope
    extraction_version

    同一个版本重新执行时：
    先删除该版本旧结果，
    再写入新结果。

    不同版本的数据可以同时保留。
    """

    ensure_facts_schema()

    connection = get_connection()

    try:

        connection.execute(
            "BEGIN"
        )

        # ====================================================
        # 1. 删除同一个抽取版本的旧 Facts
        # ====================================================

        connection.execute(
            """
            DELETE FROM facts

            WHERE document_id = ?
              AND metric_name = ?
              AND extraction_scope = ?
              AND extraction_version = ?
            """,
            (
                document_id,
                metric_spec.key,
                provenance_scope,
                extraction_version,
            ),
        )

        # ====================================================
        # 2. 删除同一个抽取版本的旧 Run 记录
        # ====================================================

        connection.execute(
            """
            DELETE FROM extraction_runs

            WHERE document_id = ?
              AND metric_name = ?
              AND extraction_scope = ?
              AND extraction_version = ?
            """,
            (
                document_id,
                metric_spec.key,
                provenance_scope,
                extraction_version,
            ),
        )

        # ====================================================
        # 3. 写入新的 Facts
        # ====================================================

        for fact in facts:

            normalized = normalize_fact(
                fact,
                metric_spec,
            )

            # ----------------------------------------------
            # 单位归一化成功：
            # 保存 normalized 数据
            # ----------------------------------------------

            if normalized.converted:

                normalized_value = (
                    normalized.value
                )

                normalized_value_min = (
                    normalized.value_min
                )

                normalized_value_max = (
                    normalized.value_max
                )

                normalized_unit = (
                    normalized.unit
                )

            # ----------------------------------------------
            # 单位归一化失败：
            # 原始数据仍然保存，
            # normalized_* 留空
            # ----------------------------------------------

            else:

                normalized_value = None
                normalized_value_min = None
                normalized_value_max = None
                normalized_unit = None

            connection.execute(
                """
                INSERT INTO facts (

                    document_id,
                    metric_name,

                    value_type,

                    raw_value,
                    raw_value_min,
                    raw_value_max,
                    raw_unit,

                    normalized_value,
                    normalized_value_min,
                    normalized_value_max,
                    normalized_unit,

                    normalization_converted,
                    normalization_error,

                    page_number,
                    source_chunk_id,

                    evidence,
                    evidence_verified,

                    condition_text,
                    provenance,
                    confidence,

                    extraction_scope,
                    extraction_version
                )

                VALUES (
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?,
                    ?, ?,
                    ?, ?,
                    ?, ?, ?,
                    ?, ?
                )
                """,
                (
                    document_id,
                    metric_spec.key,

                    fact.value_type,

                    fact.value,
                    fact.value_min,
                    fact.value_max,
                    fact.unit,

                    normalized_value,
                    normalized_value_min,
                    normalized_value_max,
                    normalized_unit,

                    int(
                        normalized.converted
                    ),

                    normalized.error,

                    fact.page_number,
                    fact.chunk_id,

                    fact.evidence,

                    int(
                        fact.evidence_verified
                    ),

                    fact.condition_text,
                    fact.provenance,
                    fact.confidence,

                    provenance_scope,
                    extraction_version,
                ),
            )

        # ====================================================
        # 4. 记录本次抽取已经成功完成
        #
        # 即使 facts == []，
        # 仍然记录 fact_count = 0。
        # ====================================================

        connection.execute(
            """
            INSERT INTO extraction_runs (

                document_id,
                metric_name,
                extraction_scope,
                extraction_version,
                status,
                fact_count
            )

            VALUES (
                ?, ?, ?, ?, ?, ?
            )
            """,
            (
                document_id,
                metric_spec.key,
                provenance_scope,
                extraction_version,
                "success",
                len(facts),
            ),
        )

        connection.commit()

    except Exception:

        connection.rollback()
        raise

    finally:

        connection.close()


def get_saved_facts(
    document_id: str | None = None,
    metric_name: str | None = None,
    extraction_scope: str | None = None,
    extraction_version: str | None = None,
) -> list[dict]:
    """
    查询已经持久化的 Facts。

    支持按照 extraction_version 精确读取，
    防止不同抽取版本的数据混在一起。
    """

    connection = get_connection()

    try:

        sql = """
        SELECT

            facts.*,

            documents.title,
            documents.filename,
            documents.local_path

        FROM facts

        JOIN documents
          ON documents.id = facts.document_id

        WHERE 1 = 1
        """

        parameters = []

        if document_id is not None:

            sql += """
            AND facts.document_id = ?
            """

            parameters.append(
                document_id
            )

        if metric_name is not None:

            sql += """
            AND facts.metric_name = ?
            """

            parameters.append(
                metric_name
            )

        if extraction_scope is not None:

            sql += """
            AND facts.extraction_scope = ?
            """

            parameters.append(
                extraction_scope
            )

        if extraction_version is not None:

            sql += """
            AND facts.extraction_version = ?
            """

            parameters.append(
                extraction_version
            )

        sql += """
        ORDER BY
            documents.title,
            facts.page_number,
            facts.id
        """

        cursor = connection.execute(
            sql,
            parameters,
        )

        column_names = [
            item[0]
            for item in cursor.description
        ]

        rows = cursor.fetchall()

        results = []

        for row in rows:

            if hasattr(
                row,
                "keys",
            ):

                results.append(
                    dict(row)
                )

            else:

                results.append(
                    dict(
                        zip(
                            column_names,
                            row,
                        )
                    )
                )

        return results

    finally:

        connection.close()


def has_cached_extraction(
    document_id: str,
    metric_name: str,
    extraction_scope: str,
    extraction_version: str,
) -> bool:
    """
    判断某篇论文的某个指标是否已经完成过抽取。

    注意：
    fact_count = 0 也属于有效缓存。
    """

    connection = get_connection()

    try:

        cursor = connection.execute(
            """
            SELECT 1

            FROM extraction_runs

            WHERE document_id = ?
              AND metric_name = ?
              AND extraction_scope = ?
              AND extraction_version = ?
              AND status = 'success'

            LIMIT 1
            """,
            (
                document_id,
                metric_name,
                extraction_scope,
                extraction_version,
            ),
        )

        return (
            cursor.fetchone()
            is not None
        )

    finally:

        connection.close()


def load_cached_facts(
    document_id: str,
    metric_name: str,
    extraction_scope: str,
    extraction_version: str,
) -> list[ExtractedFact]:
    """
    从指定 extraction_version 的缓存中
    读取 Facts。

    返回 ExtractedFact，
    让 Agent 不需要区分数据来自：
    - LLM 新抽取
    - SQLite Cache
    """

    rows = get_saved_facts(
        document_id=document_id,
        metric_name=metric_name,
        extraction_scope=extraction_scope,
        extraction_version=extraction_version,
    )

    facts = []

    for row in rows:

        fact = ExtractedFact(

            document_id=row[
                "document_id"
            ],

            metric_name=row[
                "metric_name"
            ],

            value_type=row[
                "value_type"
            ],

            value=row[
                "raw_value"
            ],

            value_min=row[
                "raw_value_min"
            ],

            value_max=row[
                "raw_value_max"
            ],

            unit=row[
                "raw_unit"
            ],

            page_number=row[
                "page_number"
            ],

            chunk_id=row[
                "source_chunk_id"
            ],

            evidence=(
                row["evidence"]
                or ""
            ),

            evidence_verified=bool(
                row["evidence_verified"]
            ),

            condition_text=row[
                "condition_text"
            ],

            provenance=row[
                "provenance"
            ],

            confidence=(
                row["confidence"]
                if row["confidence"]
                is not None
                else 0.0
            ),
        )

        facts.append(
            fact
        )

    return facts