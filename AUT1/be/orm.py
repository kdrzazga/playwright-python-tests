import math
from dataclasses import fields
from datetime import date
from types import NoneType, UnionType
from typing import get_args

from database_errors import PageOutOfRangeError, RecordNotFoundError, RelationshipNotFoundError
from simulated_load import NoSimulatedLoad, subject_to_simulated_load


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
            self._prefix_with_relationship_name(related_column_name): self.related_table.convert_to_json_compatible_value(
                getattr(related_record, related_column_name)
            )
            for related_column_name in self.displayed_related_column_names
        }

    def _prefix_with_relationship_name(self, related_column_name):
        return f"{self.relationship_name}_{related_column_name}"


class SqlTable:
    def __init__(
        self,
        connection,
        database_name,
        table_name,
        record_type,
        relationships=(),
        replica_of_qualified_table_name=None,
        primary_key_column_name="id",
        simulated_load=None,
        touches_reference_data=False,
    ):
        self.connection = connection
        self.database_name = database_name
        self.table_name = table_name
        self.record_type = record_type
        self.replica_of_qualified_table_name = replica_of_qualified_table_name
        self.primary_key_column_name = primary_key_column_name
        self.simulated_load = simulated_load or NoSimulatedLoad()
        self.touches_reference_data = touches_reference_data or replica_of_qualified_table_name is not None
        self._relationships_by_foreign_key_column_name = {
            relationship.foreign_key_column_name: relationship for relationship in relationships
        }

    @property
    def qualified_table_name(self):
        return f"{self.database_name}.{self.table_name}"

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

    def build_insert_statement(self, inserted_column_names):
        return (
            f"INSERT INTO {self.qualified_table_name} ({', '.join(inserted_column_names)}) "
            f"VALUES ({', '.join('?' for _ in inserted_column_names)})"
        )

    def build_update_by_primary_key_statement(self, updated_column_names):
        assignments = ", ".join(f"{column_name} = ?" for column_name in updated_column_names)
        return f"UPDATE {self.qualified_table_name} SET {assignments} WHERE {self.primary_key_column_name} = ?"

    @subject_to_simulated_load
    def insert_record_with_generated_id(self, **column_values):
        generated_id = self.connection.run_in_single_transaction(
            lambda transaction: transaction.execute(
                self.build_insert_statement(tuple(column_values)), tuple(column_values.values())
            ).lastrowid
        )
        return self.find_record_by_id(generated_id)

    @subject_to_simulated_load
    def update_record_by_primary_key(self, primary_key_value, **changed_column_values):
        updated_row_count = self.connection.run_in_single_transaction(
            lambda transaction: transaction.execute(
                self.build_update_by_primary_key_statement(tuple(changed_column_values)),
                (*changed_column_values.values(), primary_key_value),
            ).rowcount
        )
        if updated_row_count == 0:
            raise RecordNotFoundError(
                f"No record with {self.primary_key_column_name} {primary_key_value} in table '{self.qualified_table_name}'"
            )
        return self.find_record_by_id(primary_key_value)

    @subject_to_simulated_load
    def contains_record_with_id(self, record_id):
        return self.find_record_by_id(record_id) is not None

    @subject_to_simulated_load
    def find_record_by_id(self, record_id):
        row = self.connection.fetch_single_row(
            f"SELECT * FROM {self.qualified_table_name} WHERE {self.primary_key_column_name} = ?", (record_id,)
        )
        return None if row is None else self.map_row_to_record(row)

    @subject_to_simulated_load
    def load_related_record(self, record, relationship_name):
        for relationship in self._relationships_by_foreign_key_column_name.values():
            if relationship.relationship_name == relationship_name:
                return relationship.load_related_record_of(record)
        raise RelationshipNotFoundError(
            f"Table '{self.qualified_table_name}' has no relationship named '{relationship_name}'"
        )

    @subject_to_simulated_load
    def count_all_records(self):
        return self.connection.fetch_single_row(f"SELECT COUNT(*) FROM {self.qualified_table_name}")[0]

    @subject_to_simulated_load
    def count_pages_for_page_size(self, page_size):
        return max(1, math.ceil(self.count_all_records() / page_size))

    @subject_to_simulated_load
    def list_records_on_page(self, page_number, page_size):
        total_page_count = self.count_pages_for_page_size(page_size)
        if not 1 <= page_number <= total_page_count:
            raise PageOutOfRangeError(
                f"Page {page_number} of table '{self.qualified_table_name}' is out of range 1-{total_page_count}"
            )
        rows = self.connection.fetch_all_rows(
            f"SELECT * FROM {self.qualified_table_name} ORDER BY {self.primary_key_column_name} LIMIT ? OFFSET ?",
            (page_size, (page_number - 1) * page_size),
        )
        return [self.map_row_to_record(row) for row in rows]

    def describe_record_with_related_records(self, record):
        described_record = {}
        for column_name in self.column_names:
            relationship = self._relationships_by_foreign_key_column_name.get(column_name)
            if relationship is None:
                described_record[column_name] = self.convert_to_json_compatible_value(getattr(record, column_name))
            else:
                described_record.update(relationship.describe_related_record_of(record))
        return described_record

    @subject_to_simulated_load
    def describe_page(self, page_number, page_size):
        return {
            "database_name": self.database_name,
            "table_name": self.table_name,
            "replica_of": self.replica_of_qualified_table_name,
            "primary_key_column_name": self.primary_key_column_name,
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

    def map_row_to_record(self, row):
        return self.record_type(
            **{
                record_field.name: self._convert_column_value_to_declared_type(row[record_field.name], record_field.type)
                for record_field in fields(self.record_type)
            }
        )

    @staticmethod
    def _convert_column_value_to_declared_type(column_value, declared_type):
        if column_value is None:
            return None
        if isinstance(declared_type, UnionType):
            declared_type = next(member_type for member_type in get_args(declared_type) if member_type is not NoneType)
        if declared_type is date:
            return date.fromisoformat(column_value)
        return declared_type(column_value)

    @staticmethod
    def convert_to_json_compatible_value(record_value):
        return record_value.isoformat() if isinstance(record_value, date) else record_value
