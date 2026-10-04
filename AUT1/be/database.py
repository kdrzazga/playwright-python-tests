from dataclasses import asdict, dataclass, fields
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


class ForeignKeyViolationError(ValueError):
    pass


class InMemoryTable:
    def __init__(self, table_name, record_type):
        self.table_name = table_name
        self.record_type = record_type
        self._records_by_id = {}
        self._next_free_id = 1

    @property
    def column_names(self):
        return tuple(record_field.name for record_field in fields(self.record_type))

    def insert_record_with_generated_id(self, **column_values):
        record = self.record_type(id=self._next_free_id, **column_values)
        self._records_by_id[record.id] = record
        self._next_free_id += 1
        return record

    def contains_record_with_id(self, record_id):
        return record_id in self._records_by_id

    def find_record_by_id(self, record_id):
        return self._records_by_id.get(record_id)

    def count_all_records(self):
        return len(self._records_by_id)

    def list_records_up_to_limit(self, record_limit):
        return list(self._records_by_id.values())[:record_limit]

    def describe_with_records_up_to_limit(self, record_limit):
        return {
            "table_name": self.table_name,
            "column_names": list(self.column_names),
            "total_record_count": self.count_all_records(),
            "records": [asdict(record) for record in self.list_records_up_to_limit(record_limit)],
        }


class InMemoryDatabase:
    def __init__(self):
        self.vehicles = InMemoryTable("vehicles", Vehicle)
        self.customers = InMemoryTable("customers", Customer)
        self.sales = InMemoryTable("sales", Sale)
        self.rentals = InMemoryTable("rentals", Rental)

    def all_tables(self):
        return self.vehicles, self.customers, self.sales, self.rentals

    def add_vehicle(self, brand, model, engine, manufacture_year, used):
        return self.vehicles.insert_record_with_generated_id(
            brand=brand,
            model=model,
            engine=EngineType(engine),
            manufacture_year=manufacture_year,
            used=used,
        )

    def add_customer(self, name, address):
        return self.customers.insert_record_with_generated_id(name=name, address=address)

    def register_sale_of_vehicle_to_customer(self, vehicle_id, customer_id):
        self._ensure_vehicle_and_customer_exist(vehicle_id, customer_id)
        return self.sales.insert_record_with_generated_id(vehicle_id=vehicle_id, customer_id=customer_id)

    def register_rental_of_vehicle_to_customer(self, vehicle_id, customer_id):
        self._ensure_vehicle_and_customer_exist(vehicle_id, customer_id)
        return self.rentals.insert_record_with_generated_id(vehicle_id=vehicle_id, customer_id=customer_id)

    def describe_all_tables_with_records_up_to_limit(self, record_limit):
        return [table.describe_with_records_up_to_limit(record_limit) for table in self.all_tables()]

    def _ensure_vehicle_and_customer_exist(self, vehicle_id, customer_id):
        if not self.vehicles.contains_record_with_id(vehicle_id):
            raise ForeignKeyViolationError(f"Vehicle with id {vehicle_id} does not exist")
        if not self.customers.contains_record_with_id(customer_id):
            raise ForeignKeyViolationError(f"Customer with id {customer_id} does not exist")
