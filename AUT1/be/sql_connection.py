import sqlite3
import threading

from database_errors import IntegrityConstraintViolationError


class TransactionScope:
    def __init__(self, raw_connection):
        self._raw_connection = raw_connection

    def execute(self, sql_statement, statement_parameters=()):
        return self._raw_connection.execute(sql_statement, statement_parameters)


class ThreadSafeInMemorySqliteConnection:
    def __init__(self, attached_database_names):
        self._connection = sqlite3.connect(":memory:", check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        for database_name in attached_database_names:
            self._connection.execute(f"ATTACH DATABASE ':memory:' AS {database_name}")
        self._lock = threading.Lock()

    def run_sql_script(self, sql_script):
        with self._lock:
            self._connection.executescript(sql_script)

    def fetch_all_rows(self, sql_query, query_parameters=()):
        with self._lock:
            return self._connection.execute(sql_query, query_parameters).fetchall()

    def fetch_single_row(self, sql_query, query_parameters=()):
        with self._lock:
            return self._connection.execute(sql_query, query_parameters).fetchone()

    def run_in_single_transaction(self, unit_of_work):
        try:
            with self._lock, self._connection:
                return unit_of_work(TransactionScope(self._connection))
        except sqlite3.IntegrityError as error:
            raise IntegrityConstraintViolationError(str(error)) from error
