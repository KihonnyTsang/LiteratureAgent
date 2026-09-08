import sqlite3
from pathlib import Path


# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 数据库文件位置
DB_PATH = PROJECT_ROOT / "data" / "database" / "literature.db"


def get_connection():
    """
    创建并返回 SQLite 数据库连接。
    """

    # 确保数据库文件夹存在
    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(DB_PATH)

    # 开启 SQLite 外键约束
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def init_db():
    """
    初始化数据库。
    如果数据表不存在，则自动创建。
    """

    connection = get_connection()
    cursor = connection.cursor()

    # ==========================
    # 文献表
    # ==========================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,

            title TEXT NOT NULL,

            filename TEXT NOT NULL,

            local_path TEXT NOT NULL UNIQUE,

            page_count INTEGER,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # ==========================
    # documents schema migration
    # ==========================

    cursor.execute(
        """
        PRAGMA table_info(documents)
        """
    )

    document_columns = {
        row[1]
        for row in cursor.fetchall()
    }

    if "content_hash" not in document_columns:
        cursor.execute(
            """
            ALTER TABLE documents
            ADD COLUMN content_hash TEXT
            """
        )

    # ==========================
    # 页面表
    # ==========================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            document_id TEXT NOT NULL,

            page_number INTEGER NOT NULL,

            text TEXT,

            FOREIGN KEY (document_id)
                REFERENCES documents(id)
                ON DELETE CASCADE,

            UNIQUE(document_id, page_number)
        )
        """
    )

    # ==========================
    # Chunk 表
    # ==========================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            document_id TEXT NOT NULL,

            page_number INTEGER NOT NULL,

            chunk_index INTEGER NOT NULL,

            text TEXT NOT NULL,

            FOREIGN KEY (document_id)
                REFERENCES documents(id)
                ON DELETE CASCADE,

            UNIQUE(
                document_id,
                page_number,
                chunk_index
            )
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            document_id TEXT NOT NULL,

            metric_name TEXT NOT NULL,

            raw_value REAL,
            raw_unit TEXT,

            normalized_value REAL,
            normalized_unit TEXT,

            page_number INTEGER,

            evidence TEXT,
            condition_text TEXT,

            confidence REAL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (document_id)
                REFERENCES documents(id)
        )
        """
    )
    connection.commit()
    connection.close()

def document_exists(local_path: str) -> bool:
    """
    判断某个 PDF 是否已经入库。
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM documents
        WHERE local_path = ?
        """,
        (local_path,),
    )

    result = cursor.fetchone()

    connection.close()

    return result is not None


def insert_document_with_pages(
    document_id: str,
    title: str,
    filename: str,
    local_path: str,
    pages: list[dict],
    content_hash: str | None = None,
):
    """
    将一篇文献及其所有页面一次性写入数据库。

    使用事务保证：
    要么整篇文献全部写入成功，
    要么全部不写入。
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # 写入 documents 表
        cursor.execute(
            """
            INSERT INTO documents (
                id,
                title,
                filename,
                local_path,
                page_count,
                content_hash
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                title,
                filename,
                local_path,
                len(pages),
                content_hash,
            ),
        )

        # 写入 pages 表
        page_records = [
            (
                document_id,
                page["page_number"],
                page["text"],
            )
            for page in pages
        ]

        cursor.executemany(
            """
            INSERT INTO pages (
                document_id,
                page_number,
                text
            )
            VALUES (?, ?, ?)
            """,
            page_records,
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def get_all_pages() -> list[dict]:
    """
    获取数据库中的所有页面。
    """

    connection = get_connection()

    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            document_id,
            page_number,
            text
        FROM pages
        ORDER BY
            document_id,
            page_number
        """
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]

def chunks_exist(
    document_id: str,
    page_number: int,
) -> bool:
    """
    判断某一页是否已经生成 Chunk。
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM chunks
        WHERE
            document_id = ?
            AND page_number = ?
        LIMIT 1
        """,
        (
            document_id,
            page_number,
        ),
    )

    result = cursor.fetchone()

    connection.close()

    return result is not None

def insert_chunks(
    document_id: str,
    page_number: int,
    chunks: list[str],
):
    """
    将某一页的所有 Chunk 写入数据库。
    """

    if not chunks:
        return

    connection = get_connection()

    try:
        cursor = connection.cursor()

        records = [
            (
                document_id,
                page_number,
                chunk_index,
                text,
            )
            for chunk_index, text in enumerate(chunks)
        ]

        cursor.executemany(
            """
            INSERT INTO chunks (
                document_id,
                page_number,
                chunk_index,
                text
            )
            VALUES (?, ?, ?, ?)
            """,
            records,
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

def get_all_chunks() -> list[dict]:
    """
    获取所有 Chunk，并同时读取对应文献的信息。
    """

    connection = get_connection()

    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            chunks.id AS chunk_id,
            chunks.document_id,
            chunks.page_number,
            chunks.chunk_index,
            chunks.text,

            documents.title,
            documents.filename,
            documents.local_path

        FROM chunks

        JOIN documents
            ON chunks.document_id = documents.id

        ORDER BY
            chunks.document_id,
            chunks.page_number,
            chunks.chunk_index
        """
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]

def get_all_documents() -> list[dict]:
    """
    获取所有文档的基础元数据。

    这个函数作为 Document Metadata Tool
    的底层数据接口，因此应返回 documents 表中
    Agent 允许查询的元数据字段。
    """

    connection = get_connection()

    try:

        cursor = connection.execute(
            """
            SELECT
                id,
                title,
                filename,
                local_path,
                page_count

            FROM documents

            ORDER BY created_at, id
            """
        )

        rows = cursor.fetchall()

        # 如果 get_connection() 使用 sqlite3.Row
        if rows and hasattr(
            rows[0],
            "keys",
        ):

            return [
                dict(row)
                for row in rows
            ]

        # 兼容普通 tuple
        column_names = [
            item[0]
            for item in cursor.description
        ]

        return [
            dict(
                zip(
                    column_names,
                    row,
                )
            )
            for row in rows
        ]

    finally:

        connection.close()

def insert_fact(
    document_id: str,
    metric_name: str,
    raw_value: float | None,
    raw_unit: str | None,
    normalized_value: float | None,
    normalized_unit: str | None,
    page_number: int | None,
    evidence: str | None,
    condition_text: str | None,
    confidence: float | None,
):
    """
    保存一条结构化科研数据。
    """

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO facts (
            document_id,
            metric_name,
            raw_value,
            raw_unit,
            normalized_value,
            normalized_unit,
            page_number,
            evidence,
            condition_text,
            confidence
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            document_id,
            metric_name,
            raw_value,
            raw_unit,
            normalized_value,
            normalized_unit,
            page_number,
            evidence,
            condition_text,
            confidence,
        ),
    )

    connection.commit()
    connection.close()

def get_documents_for_sync() -> list[dict]:
    """
    Knowledge Base Sync 专用接口。

    content_hash 是基础设施字段，
    不应该暴露给普通 Metadata Tool。
    """

    connection = get_connection()
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.execute(
            """
            SELECT
                id,
                title,
                filename,
                local_path,
                content_hash
            FROM documents
            ORDER BY created_at, id
            """
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:
        connection.close()


def update_document_content_hash(
    document_id: str,
    content_hash: str,
) -> None:
    """
    为旧版本数据库中的文档补写 SHA256。
    """

    connection = get_connection()

    try:
        connection.execute(
            """
            UPDATE documents
            SET content_hash = ?
            WHERE id = ?
            """,
            (
                content_hash,
                document_id,
            ),
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def table_exists(
    connection: sqlite3.Connection,
    table_name: str,
) -> bool:
    """
    判断 SQLite 表是否存在。
    """

    cursor = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        LIMIT 1
        """,
        (
            table_name,
        ),
    )

    return (
        cursor.fetchone()
        is not None
    )


def delete_document_data(
    document_id: str,
) -> None:
    """
    删除某篇文献在 SQLite 中的全部派生状态。

    pages / chunks：
        通过 documents 外键 ON DELETE CASCADE 删除。

    facts / extraction_runs：
        显式删除，避免旧科研事实缓存残留。
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        if table_exists(
            connection,
            "facts",
        ):
            cursor.execute(
                """
                DELETE FROM facts
                WHERE document_id = ?
                """,
                (
                    document_id,
                ),
            )

        if table_exists(
            connection,
            "extraction_runs",
        ):
            cursor.execute(
                """
                DELETE FROM extraction_runs
                WHERE document_id = ?
                """,
                (
                    document_id,
                ),
            )

        cursor.execute(
            """
            DELETE FROM documents
            WHERE id = ?
            """,
            (
                document_id,
            ),
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()