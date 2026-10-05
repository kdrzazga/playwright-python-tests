from database_errors import RecordNotFoundError
from simulated_load import NoSimulatedLoad, subject_to_simulated_load


class ReplicatedReferenceTable:
    def __init__(self, connection, master_table, replica_table, replication_guard_table_name, simulated_load=None):
        self.connection = connection
        self.master_table = master_table
        self.replica_table = replica_table
        self.replication_guard_table_name = replication_guard_table_name
        self.simulated_load = simulated_load or NoSimulatedLoad()
        self.touches_reference_data = True

    @property
    def replication_guard_qualified_table_name(self):
        return f"{self.replica_table.database_name}.{self.replication_guard_table_name}"

    @property
    def primary_key_column_name(self):
        return self.master_table.primary_key_column_name

    def install_triggers_rejecting_direct_writes_to_replica(self):
        rejection_message = (
            f"{self.replica_table.qualified_table_name} is a read-only replica of "
            f"{self.master_table.qualified_table_name}"
        )
        trigger_definitions = [
            f"CREATE TRIGGER {self.replica_table.database_name}."
            f"{self.replica_table.table_name}_replica_rejects_direct_{write_operation.lower()}\n"
            f"BEFORE {write_operation} ON {self.replica_table.table_name}\n"
            f"WHEN (SELECT replication_in_progress FROM {self.replication_guard_table_name}) = 0\n"
            f"BEGIN\n    SELECT RAISE(ABORT, '{rejection_message}');\nEND;"
            for write_operation in ("INSERT", "UPDATE", "DELETE")
        ]
        self.connection.run_sql_script("\n".join(trigger_definitions))

    def refresh_whole_replica_from_master(self):
        self.connection.run_in_single_transaction(
            lambda transaction: self._copy_master_rows_to_replica(transaction, "WHERE true", ())
        )

    @subject_to_simulated_load
    def insert_into_master_and_replicate(self, **column_values):
        new_primary_key_value = self.connection.run_in_single_transaction(
            lambda transaction: self.insert_into_master_and_replicate_within_transaction(transaction, **column_values)
        )
        return self.master_table.find_record_by_id(new_primary_key_value)

    def insert_into_master_and_replicate_within_transaction(self, transaction, **column_values):
        insert_cursor = transaction.execute(
            self.master_table.build_insert_statement(tuple(column_values)), tuple(column_values.values())
        )
        if self.primary_key_column_name in column_values:
            new_primary_key_value = column_values[self.primary_key_column_name]
        else:
            new_primary_key_value = insert_cursor.lastrowid
        self._copy_master_rows_to_replica(
            transaction, f"WHERE {self.primary_key_column_name} = ?", (new_primary_key_value,)
        )
        return new_primary_key_value

    @subject_to_simulated_load
    def update_master_record_and_replicate(self, primary_key_value, **changed_column_values):
        self.connection.run_in_single_transaction(
            lambda transaction: self.update_master_record_and_replicate_within_transaction(
                transaction, primary_key_value, **changed_column_values
            )
        )
        return self.master_table.find_record_by_id(primary_key_value)

    def update_master_record_and_replicate_within_transaction(self, transaction, primary_key_value, **changed_column_values):
        updated_row_count = transaction.execute(
            self.master_table.build_update_by_primary_key_statement(tuple(changed_column_values)),
            (*changed_column_values.values(), primary_key_value),
        ).rowcount
        if updated_row_count == 0:
            raise RecordNotFoundError(
                f"No record with {self.primary_key_column_name} {primary_key_value} "
                f"in table '{self.master_table.qualified_table_name}'"
            )
        self._copy_master_rows_to_replica(transaction, f"WHERE {self.primary_key_column_name} = ?", (primary_key_value,))

    def copy_master_record_to_replica_within_transaction(self, transaction, primary_key_value):
        self._copy_master_rows_to_replica(transaction, f"WHERE {self.primary_key_column_name} = ?", (primary_key_value,))

    def _copy_master_rows_to_replica(self, transaction, master_row_filter, filter_parameters):
        column_list = ", ".join(self.master_table.column_names)
        column_updates_on_existing_replica_row = ", ".join(
            f"{column_name} = excluded.{column_name}"
            for column_name in self.master_table.column_names
            if column_name != self.primary_key_column_name
        )
        self._set_replication_in_progress(transaction, True)
        transaction.execute(
            f"INSERT INTO {self.replica_table.qualified_table_name} ({column_list}) "
            f"SELECT {column_list} FROM {self.master_table.qualified_table_name} {master_row_filter} "
            f"ON CONFLICT ({self.primary_key_column_name}) DO UPDATE SET {column_updates_on_existing_replica_row}",
            filter_parameters,
        )
        self._set_replication_in_progress(transaction, False)

    def _set_replication_in_progress(self, transaction, replication_in_progress):
        transaction.execute(
            f"UPDATE {self.replication_guard_qualified_table_name} SET replication_in_progress = ?",
            (int(replication_in_progress),),
        )
