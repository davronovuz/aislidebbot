"""PostgreSQL backend — drop-in replacement for the old SQLite Database class."""
import os
import logging
import psycopg2

logger = logging.getLogger(__name__)

DATABASE_URL_SYNC = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql://aislide:aislide_pg_2026@postgres:5432/aislide",
)


class Database:
    def __init__(self, path_to_db=None):
        # path_to_db kept for backward-compat but ignored
        pass

    def _connect(self):
        return psycopg2.connect(DATABASE_URL_SYNC)

    def execute(
        self,
        sql: str,
        parameters: tuple = None,
        fetchone: bool = False,
        fetchall: bool = False,
        commit: bool = False,
    ):
        if parameters is None:
            parameters = ()
        # Convert SQLite ? placeholders → psycopg2 %s
        sql = sql.replace("?", "%s")

        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, parameters)
                data = None
                if fetchone:
                    data = cur.fetchone()
                elif fetchall:
                    data = cur.fetchall()
                if commit:
                    conn.commit()
                return data
        except psycopg2.Error as e:
            logger.error("PostgreSQL error: %s | SQL: %.200s", e, sql)
            conn.rollback()
            return None
        finally:
            conn.close()

    def execute_returning(self, sql: str, parameters: tuple = None) -> int | None:
        """Execute INSERT ... RETURNING id and return the generated id."""
        if parameters is None:
            parameters = ()
        sql = sql.replace("?", "%s")
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, parameters)
                row = cur.fetchone()
                conn.commit()
                return row[0] if row else None
        except psycopg2.Error as e:
            logger.error("PostgreSQL error (returning): %s | SQL: %.200s", e, sql)
            conn.rollback()
            return None
        finally:
            conn.close()

    @staticmethod
    def format_args(sql, parameters: dict):
        sql += " AND ".join([f"{item} = %s" for item in parameters])
        return sql, tuple(parameters.values())
