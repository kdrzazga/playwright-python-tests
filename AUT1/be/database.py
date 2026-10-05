from database_errors import TableNotFoundError
from orm import ManyToOneRelationship, SqlTable
from records import (
    BodyStyle,
    CommercialPolicy,
    Company,
    CompanyType,
    Customer,
    CustomerType,
    Drivetrain,
    EngineType,
    IndividualCustomer,
    InstitutionalCustomer,
    Loan,
    Rental,
    RentalAgreement,
    Sale,
    SaleAgreement,
    Transmission,
    Vehicle,
    VehicleCondition,
)
from replication import ReplicatedReferenceTable
from sql_connection import ThreadSafeInMemorySqliteConnection


class InMemoryDatabase:
    def __init__(
        self,
        connection,
        reference_database_name="reference",
        dealership_database_name="dealership",
        replication_guard_table_name="replication_guard",
        displayed_vehicle_column_names=("id", "brand", "model", "manufacture_year"),
        displayed_customer_column_names=("id", "name"),
        displayed_lender_column_names=("id", "name"),
    ):
        self.connection = connection
        self.reference_customers = SqlTable(connection, reference_database_name, "customers", Customer)
        self.reference_individual_customers = SqlTable(
            connection, reference_database_name, "individual_customers", IndividualCustomer,
            primary_key_column_name="customer_id",
        )
        self.reference_institutional_customers = SqlTable(
            connection, reference_database_name, "institutional_customers", InstitutionalCustomer,
            primary_key_column_name="customer_id",
        )
        self.reference_companies = SqlTable(connection, reference_database_name, "companies", Company)
        self.reference_commercial_policy = SqlTable(
            connection, reference_database_name, "commercial_policy", CommercialPolicy
        )

        self.vehicles = SqlTable(connection, dealership_database_name, "vehicles", Vehicle)
        self.customers = self._build_replica_of(self.reference_customers, dealership_database_name)
        self.individual_customers = self._build_replica_of(self.reference_individual_customers, dealership_database_name)
        self.institutional_customers = self._build_replica_of(
            self.reference_institutional_customers, dealership_database_name
        )
        self.companies = self._build_replica_of(self.reference_companies, dealership_database_name)
        self.commercial_policy = self._build_replica_of(self.reference_commercial_policy, dealership_database_name)

        customer_relationship = ManyToOneRelationship(
            "customer", "customer_id", self.customers, displayed_customer_column_names
        )
        vehicle_relationship = ManyToOneRelationship(
            "vehicle", "vehicle_id", self.vehicles, displayed_vehicle_column_names
        )
        self.sale_agreements = SqlTable(
            connection, dealership_database_name, "sale_agreements", SaleAgreement, (customer_relationship,)
        )
        self.sales = SqlTable(connection, dealership_database_name, "sales", Sale, (vehicle_relationship,))
        self.rental_agreements = SqlTable(
            connection, dealership_database_name, "rental_agreements", RentalAgreement, (customer_relationship,)
        )
        self.rentals = SqlTable(connection, dealership_database_name, "rentals", Rental, (vehicle_relationship,))
        lender_relationship = ManyToOneRelationship(
            "lender", "lender_company_id", self.companies, displayed_lender_column_names
        )
        self.loans = SqlTable(connection, dealership_database_name, "loans", Loan, (lender_relationship,))

        self.replication_guard_table_name = replication_guard_table_name
        self.customer_replication = self._build_replication(self.reference_customers, self.customers)
        self.individual_customer_replication = self._build_replication(
            self.reference_individual_customers, self.individual_customers
        )
        self.institutional_customer_replication = self._build_replication(
            self.reference_institutional_customers, self.institutional_customers
        )
        self.company_replication = self._build_replication(self.reference_companies, self.companies)
        self.commercial_policy_replication = self._build_replication(
            self.reference_commercial_policy, self.commercial_policy
        )

    @classmethod
    def create_from_sql_scripts_in_directory(
        cls,
        sql_directory,
        reference_database_name="reference",
        dealership_database_name="dealership",
    ):
        connection = ThreadSafeInMemorySqliteConnection((reference_database_name, dealership_database_name))
        for sql_script_path in (
            sql_directory / reference_database_name / "schema.sql",
            sql_directory / reference_database_name / "seed_data.sql",
            sql_directory / dealership_database_name / "schema.sql",
        ):
            connection.run_sql_script(sql_script_path.read_text(encoding="utf-8"))
        database = cls(connection, reference_database_name, dealership_database_name)
        database.install_triggers_rejecting_direct_writes_to_all_replicas()
        database.refresh_all_replicas_from_reference_database()
        connection.run_sql_script((sql_directory / dealership_database_name / "seed_data.sql").read_text(encoding="utf-8"))
        return database

    def all_tables(self):
        return (
            self.reference_customers,
            self.reference_individual_customers,
            self.reference_institutional_customers,
            self.reference_companies,
            self.reference_commercial_policy,
            self.vehicles,
            self.customers,
            self.individual_customers,
            self.institutional_customers,
            self.companies,
            self.commercial_policy,
            self.sale_agreements,
            self.sales,
            self.rental_agreements,
            self.rentals,
            self.loans,
        )

    def all_replications_with_parent_tables_first(self):
        return (
            self.customer_replication,
            self.individual_customer_replication,
            self.institutional_customer_replication,
            self.company_replication,
            self.commercial_policy_replication,
        )

    def install_triggers_rejecting_direct_writes_to_all_replicas(self):
        for replication in self.all_replications_with_parent_tables_first():
            replication.install_triggers_rejecting_direct_writes_to_replica()

    def refresh_all_replicas_from_reference_database(self):
        for replication in self.all_replications_with_parent_tables_first():
            replication.refresh_whole_replica_from_master()

    def add_vehicle(
        self,
        brand,
        model,
        engine,
        manufacture_year,
        used,
        body_style,
        transmission,
        drivetrain,
        power_hp,
        torque_nm,
        number_of_doors,
        number_of_seats,
        color,
        mileage_km,
        vin,
        registration,
        condition,
        price_eur,
        daily_rental_rate_eur,
    ):
        return self.vehicles.insert_record_with_generated_id(
            brand=brand,
            model=model,
            engine=EngineType(engine).value,
            manufacture_year=manufacture_year,
            used=used,
            body_style=BodyStyle(body_style).value,
            transmission=Transmission(transmission).value,
            drivetrain=Drivetrain(drivetrain).value,
            power_hp=power_hp,
            torque_nm=torque_nm,
            number_of_doors=number_of_doors,
            number_of_seats=number_of_seats,
            color=color,
            mileage_km=mileage_km,
            vin=vin,
            registration=registration,
            condition=VehicleCondition(condition).value,
            price_eur=price_eur,
            daily_rental_rate_eur=daily_rental_rate_eur,
        )

    def add_individual_customer(self, name, address, date_of_birth):
        def insert_customer_and_individual_details(transaction):
            customer_id = self.customer_replication.insert_into_master_and_replicate_within_transaction(
                transaction, customer_type=CustomerType.INDIVIDUAL.value, name=name, address=address
            )
            self.individual_customer_replication.insert_into_master_and_replicate_within_transaction(
                transaction,
                customer_id=customer_id,
                customer_type=CustomerType.INDIVIDUAL.value,
                date_of_birth=date_of_birth.isoformat(),
            )
            return customer_id

        return self.reference_customers.find_record_by_id(
            self.connection.run_in_single_transaction(insert_customer_and_individual_details)
        )

    def add_institutional_customer(
        self,
        name,
        address,
        tax_id,
        company_registration_number,
        contact_person,
        negotiated_fleet_discount_pct=None,
    ):
        def insert_customer_and_institutional_details(transaction):
            customer_id = self.customer_replication.insert_into_master_and_replicate_within_transaction(
                transaction, customer_type=CustomerType.INSTITUTIONAL.value, name=name, address=address
            )
            self.institutional_customer_replication.insert_into_master_and_replicate_within_transaction(
                transaction,
                customer_id=customer_id,
                customer_type=CustomerType.INSTITUTIONAL.value,
                tax_id=tax_id,
                company_registration_number=company_registration_number,
                contact_person=contact_person,
                negotiated_fleet_discount_pct=negotiated_fleet_discount_pct,
            )
            return customer_id

        return self.reference_customers.find_record_by_id(
            self.connection.run_in_single_transaction(insert_customer_and_institutional_details)
        )

    def update_customer(self, customer_id, **changed_column_values):
        return self.customer_replication.update_master_record_and_replicate(customer_id, **changed_column_values)

    def update_institutional_customer(self, customer_id, **changed_column_values):
        return self.institutional_customer_replication.update_master_record_and_replicate(
            customer_id, **changed_column_values
        )

    def add_company(self, name, company_type, tax_id, address):
        return self.company_replication.insert_into_master_and_replicate(
            name=name,
            company_type=CompanyType(company_type).value,
            tax_id=tax_id,
            address=address,
        )

    def update_company(self, company_id, **changed_column_values):
        return self.company_replication.update_master_record_and_replicate(company_id, **changed_column_values)

    def update_commercial_policy(self, commercial_policy_id, **changed_column_values):
        return self.commercial_policy_replication.update_master_record_and_replicate(
            commercial_policy_id, **changed_column_values
        )

    def find_table(self, database_name, table_name):
        for table in self.all_tables():
            if table.database_name == database_name and table.table_name == table_name:
                return table
        raise TableNotFoundError(f"Table '{database_name}.{table_name}' does not exist")

    def describe_first_page_of_all_tables(self, page_size):
        return [table.describe_page(1, page_size) for table in self.all_tables()]

    def _build_replication(self, master_table, replica_table):
        return ReplicatedReferenceTable(self.connection, master_table, replica_table, self.replication_guard_table_name)

    def _build_replica_of(self, master_table, replica_database_name):
        return SqlTable(
            self.connection,
            replica_database_name,
            master_table.table_name,
            master_table.record_type,
            replica_of_qualified_table_name=master_table.qualified_table_name,
            primary_key_column_name=master_table.primary_key_column_name,
        )
