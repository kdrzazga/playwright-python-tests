import math
import sqlite3
import threading
from dataclasses import dataclass, fields
from enum import StrEnum


class EngineType(StrEnum):
    DIESEL = "diesel"
    OIL = "oil"
    ELECTRIC = "electric"


@dataclass(frozen=True)
class Vehicle:
    id: int
    brand: str
    model: str
    engine: EngineType
    manufacture_year: int
    used: bool


@dataclass(frozen=True)
class Customer:
    id: int
    name: str
    address: str


@dataclass(frozen=True)
class Sale:
    id: int
    vehicle_id: int
    customer_id: int


@dataclass(frozen=True)
class Rental:
    id: int
    vehicle_id: int
    customer_id: int


class IntegrityConstraintViolationError(ValueError):
    pass


class TableNotFoundError(LookupError):
    pass


class RelationshipNotFoundError(LookupError):
    pass


class PageOutOfRangeError(ValueError):
    pass


class ThreadSafeInMemorySqliteConnection:
    def __init__(self):
        self._connection = sqlite3.connect(":memory:", check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
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

    def insert_row_and_return_generated_id(self, sql_statement, statement_parameters):
        with self._lock, self._connection:
            return self._connection.execute(sql_statement, statement_parameters).lastrowid


class ManyToOneRelationship:
    def __init__(self, relationship_name, foreign_key_column_name, related_table, displayed_related_column_names):
        self.relationship_name = relationship_name
        self.foreign_key_column_name = foreign_key_column_name
        self.related_table = related_table
        self.displayed_related_column_names = displayed_related_column_names

    @property
    def displayed_column_names(self):
        return tuple(
            self._prefix_with_relationship_name(related_column_name)
            for related_column_name in self.displayed_related_column_names
        )

    def load_related_record_of(self, record):
        return self.related_table.find_record_by_id(getattr(record, self.foreign_key_column_name))

    def describe_related_record_of(self, record):
        related_record = self.load_related_record_of(record)
        return {
            self._prefix_with_relationship_name(related_column_name): getattr(related_record, related_column_name)
            for related_column_name in self.displayed_related_column_names
        }

    def _prefix_with_relationship_name(self, related_column_name):
        return f"{self.relationship_name}_{related_column_name}"


class SqlTable:
    def __init__(self, connection, table_name, record_type, relationships=()):
        self.connection = connection
        self.table_name = table_name
        self.record_type = record_type
        self._relationships_by_foreign_key_column_name = {
            relationship.foreign_key_column_name: relationship for relationship in relationships
        }

    @property
    def column_names(self):
        return tuple(record_field.name for record_field in fields(self.record_type))

    @property
    def displayed_column_names(self):
        displayed_column_names = []
        for column_name in self.column_names:
            relationship = self._relationships_by_foreign_key_column_name.get(column_name)
            if relationship is None:
                displayed_column_names.append(column_name)
            else:
                displayed_column_names.extend(relationship.displayed_column_names)
        return tuple(displayed_column_names)

    def insert_record_with_generated_id(self, **column_values):
        inserted_column_names = tuple(column_values)
        sql_statement = (
            f"INSERT INTO {self.table_name} ({', '.join(inserted_column_names)}) "
            f"VALUES ({', '.join('?' for _ in inserted_column_names)})"
        )
        try:
            generated_id = self.connection.insert_row_and_return_generated_id(
                sql_statement, tuple(column_values.values())
            )
        except sqlite3.IntegrityError as error:
            raise IntegrityConstraintViolationError(f"Cannot insert into '{self.table_name}': {error}") from error
        return self.find_record_by_id(generated_id)

    def contains_record_with_id(self, record_id):
        return self.find_record_by_id(record_id) is not None

    def find_record_by_id(self, record_id):
        row = self.connection.fetch_single_row(f"SELECT * FROM {self.table_name} WHERE id = ?", (record_id,))
        return None if row is None else self._map_row_to_record(row)

    def load_related_record(self, record, relationship_name):
        for relationship in self._relationships_by_foreign_key_column_name.values():
            if relationship.relationship_name == relationship_name:
                return relationship.load_related_record_of(record)
        raise RelationshipNotFoundError(f"Table '{self.table_name}' has no relationship named '{relationship_name}'")

    def count_all_records(self):
        return self.connection.fetch_single_row(f"SELECT COUNT(*) FROM {self.table_name}")[0]

    def count_pages_for_page_size(self, page_size):
        return max(1, math.ceil(self.count_all_records() / page_size))

    def list_records_on_page(self, page_number, page_size):
        total_page_count = self.count_pages_for_page_size(page_size)
        if not 1 <= page_number <= total_page_count:
            raise PageOutOfRangeError(
                f"Page {page_number} of table '{self.table_name}' is out of range 1-{total_page_count}"
            )
        rows = self.connection.fetch_all_rows(
            f"SELECT * FROM {self.table_name} ORDER BY id LIMIT ? OFFSET ?",
            (page_size, (page_number - 1) * page_size),
        )
        return [self._map_row_to_record(row) for row in rows]

    def describe_record_with_related_records(self, record):
        described_record = {}
        for column_name in self.column_names:
            relationship = self._relationships_by_foreign_key_column_name.get(column_name)
            if relationship is None:
                described_record[column_name] = getattr(record, column_name)
            else:
                described_record.update(relationship.describe_related_record_of(record))
        return described_record

    def describe_page(self, page_number, page_size):
        return {
            "table_name": self.table_name,
            "column_names": list(self.displayed_column_names),
            "total_record_count": self.count_all_records(),
            "page_number": page_number,
            "page_size": page_size,
            "total_page_count": self.count_pages_for_page_size(page_size),
            "records": [
                self.describe_record_with_related_records(record)
                for record in self.list_records_on_page(page_number, page_size)
            ],
        }

    def _map_row_to_record(self, row):
        return self.record_type(
            **{record_field.name: record_field.type(row[record_field.name]) for record_field in fields(self.record_type)}
        )


class InMemoryDatabase:
    def __init__(
        self,
        connection,
        displayed_vehicle_column_names=("id", "brand", "model", "manufacture_year"),
        displayed_customer_column_names=("id", "name"),
    ):
        self.connection = connection
        self.vehicles = SqlTable(connection, "vehicles", Vehicle)
        self.customers = SqlTable(connection, "customers", Customer)
        self.sales = SqlTable(
            connection,
            "sales",
            Sale,
            self._build_vehicle_and_customer_relationships(displayed_vehicle_column_names, displayed_customer_column_names),
        )
        self.rentals = SqlTable(
            connection,
            "rentals",
            Rental,
            self._build_vehicle_and_customer_relationships(displayed_vehicle_column_names, displayed_customer_column_names),
        )

    @classmethod
    def create_by_running_sql_scripts(cls, sql_script_paths):
        connection = ThreadSafeInMemorySqliteConnection()
        for sql_script_path in sql_script_paths:
            connection.run_sql_script(sql_script_path.read_text(encoding="utf-8"))
        return cls(connection)

    def all_tables(self):
        return self.vehicles, self.customers, self.sales, self.rentals

    def add_vehicle(self, brand, model, engine, manufacture_year, used):
        return self.vehicles.insert_record_with_generated_id(
            brand=brand,
            model=model,
            engine=EngineType(engine).value,
            manufacture_year=manufacture_year,
            used=used,
        )

    def add_customer(self, name, address):
        return self.customers.insert_record_with_generated_id(name=name, address=address)

    def register_sale_of_vehicle_to_customer(self, vehicle_id, customer_id):
        return self.sales.insert_record_with_generated_id(vehicle_id=vehicle_id, customer_id=customer_id)

    def register_rental_of_vehicle_to_customer(self, vehicle_id, customer_id):
        return self.rentals.insert_record_with_generated_id(vehicle_id=vehicle_id, customer_id=customer_id)

    def find_table_by_name(self, table_name):
        for table in self.all_tables():
            if table.table_name == table_name:
                return table
        raise TableNotFoundError(f"Table '{table_name}' does not exist")

    def describe_first_page_of_all_tables(self, page_size):
        return [table.describe_page(1, page_size) for table in self.all_tables()]

    def _build_vehicle_and_customer_relationships(self, displayed_vehicle_column_names, displayed_customer_column_names):
        return (
            ManyToOneRelationship("vehicle", "vehicle_id", self.vehicles, displayed_vehicle_column_names),
            ManyToOneRelationship("customer", "customer_id", self.customers, displayed_customer_column_names),
        )
