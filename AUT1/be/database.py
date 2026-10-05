from database_errors import TableNotFoundError
from orm import ManyToOneRelationship, SqlTable
from records import (
    BodyStyle,
    Brand,
    CommercialPolicy,
    Company,
    CompanyType,
    Customer,
    CustomerType,
    Drivetrain,
    EngineType,
    Factory,
    IndividualCustomer,
    InstitutionalCustomer,
    Loan,
    PermissionDefinition,
    Rental,
    RolePermissionRule,
    RentalAgreement,
    Sale,
    SaleAgreement,
    Transmission,
    UserAccount,
    UserPermission,
    Vehicle,
    VehicleCondition,
)
from replication import ReplicatedReferenceTable
from simulated_load import NoSimulatedLoad, subject_to_simulated_load
from sql_connection import ThreadSafeInMemorySqliteConnection


class InMemoryDatabase:
    def __init__(
        self,
        connection,
        reference_database_name="reference",
        dealership_database_name="dealership",
        security_database_name="security",
        replication_guard_table_name="replication_guard",
        displayed_vehicle_column_names=("id", "brand", "model", "manufacture_year"),
        displayed_customer_column_names=("id", "name"),
        displayed_lender_column_names=("id", "name"),
        simulated_load=None,
    ):
        self.connection = connection
        self.reference_database_name = reference_database_name
        self.simulated_load = simulated_load or NoSimulatedLoad()
        self.touches_reference_data = False

        self.reference_customers = self._build_table(reference_database_name, "customers", Customer)
        self.reference_individual_customers = self._build_table(
            reference_database_name, "individual_customers", IndividualCustomer, primary_key_column_name="customer_id"
        )
        self.reference_institutional_customers = self._build_table(
            reference_database_name, "institutional_customers", InstitutionalCustomer,
            primary_key_column_name="customer_id",
        )
        self.reference_companies = self._build_table(reference_database_name, "companies", Company)
        self.reference_commercial_policy = self._build_table(
            reference_database_name, "commercial_policy", CommercialPolicy
        )
        self.reference_factories = self._build_table(reference_database_name, "factories", Factory)
        self.reference_brands = self._build_table(reference_database_name, "brands", Brand)

        self.brands = self._build_replica_of(self.reference_brands, dealership_database_name)
        self.vehicles = self._build_table(dealership_database_name, "vehicles", Vehicle)
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
        lender_relationship = ManyToOneRelationship(
            "lender", "lender_company_id", self.companies, displayed_lender_column_names
        )
        self.sale_agreements = self._build_table(
            dealership_database_name, "sale_agreements", SaleAgreement, (customer_relationship,)
        )
        self.sales = self._build_table(dealership_database_name, "sales", Sale, (vehicle_relationship,))
        self.rental_agreements = self._build_table(
            dealership_database_name, "rental_agreements", RentalAgreement, (customer_relationship,)
        )
        self.rentals = self._build_table(dealership_database_name, "rentals", Rental, (vehicle_relationship,))
        self.loans = self._build_table(dealership_database_name, "loans", Loan, (lender_relationship,))

        self.security_companies = self._build_replica_of(self.reference_companies, security_database_name)
        self.security_brands = self._build_replica_of(self.reference_brands, security_database_name)
        employer_company_relationship = ManyToOneRelationship(
            "company", "company_id", self.security_companies, ("id", "name")
        )
        self.users = self._build_table(
            security_database_name, "users", UserAccount, (employer_company_relationship,),
            hidden_column_names=("password_hash",),
        )
        brand_of_permission_relationship = ManyToOneRelationship(
            "brand", "brand_id", self.security_brands, ("id", "name")
        )
        self.permissions = self._build_table(
            security_database_name, "permissions", PermissionDefinition, (brand_of_permission_relationship,)
        )
        self.role_permission_rules = self._build_table(security_database_name, "role_permission_rules", RolePermissionRule)
        granted_user_relationship = ManyToOneRelationship("user", "user_id", self.users, ("id", "username"))
        granted_permission_relationship = ManyToOneRelationship(
            "permission", "permission_id", self.permissions, ("id", "permission"),
            displayed_column_labels={"permission": "permission"},
        )
        self.user_permissions = self._build_table(
            security_database_name, "user_permission", UserPermission,
            (granted_user_relationship, granted_permission_relationship),
        )

        self.replication_guard_table_name = replication_guard_table_name
        self.customer_replication = self._build_replication(self.reference_customers, self.customers)
        self.individual_customer_replication = self._build_replication(
            self.reference_individual_customers, self.individual_customers
        )
        self.institutional_customer_replication = self._build_replication(
            self.reference_institutional_customers, self.institutional_customers
        )
        self.brand_replication = self._build_replication(self.reference_brands, self.brands)
        self.security_brand_replication = self._build_replication(self.reference_brands, self.security_brands)
        self.company_replication = self._build_replication(self.reference_companies, self.companies)
        self.security_company_replication = self._build_replication(self.reference_companies, self.security_companies)
        self.commercial_policy_replication = self._build_replication(
            self.reference_commercial_policy, self.commercial_policy
        )

    @classmethod
    def create_from_sql_scripts_in_directory(
        cls,
        sql_directory,
        reference_database_name="reference",
        dealership_database_name="dealership",
        security_database_name="security",
        simulated_load=None,
    ):
        connection = ThreadSafeInMemorySqliteConnection(
            (reference_database_name, dealership_database_name, security_database_name)
        )
        for sql_script_path in (
            sql_directory / reference_database_name / "schema.sql",
            sql_directory / reference_database_name / "seed_data.sql",
            sql_directory / dealership_database_name / "schema.sql",
            sql_directory / security_database_name / "schema.sql",
        ):
            connection.run_sql_script(sql_script_path.read_text(encoding="utf-8"))
        database = cls(
            connection,
            reference_database_name,
            dealership_database_name,
            security_database_name,
            simulated_load=simulated_load,
        )
        database.install_triggers_rejecting_direct_writes_to_all_replicas()
        database.refresh_all_replicas_from_reference_database()
        for sql_script_path in (
            sql_directory / dealership_database_name / "seed_data.sql",
            sql_directory / security_database_name / "seed_data.sql",
        ):
            connection.run_sql_script(sql_script_path.read_text(encoding="utf-8"))
        return database

    def all_tables(self):
        return (
            self.reference_customers,
            self.reference_individual_customers,
            self.reference_institutional_customers,
            self.reference_companies,
            self.reference_commercial_policy,
            self.reference_factories,
            self.reference_brands,
            self.brands,
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
            self.security_companies,
            self.security_brands,
            self.users,
            self.permissions,
            self.role_permission_rules,
            self.user_permissions,
        )

    def all_replications_with_parent_tables_first(self):
        return (
            self.brand_replication,
            self.security_brand_replication,
            self.customer_replication,
            self.individual_customer_replication,
            self.institutional_customer_replication,
            self.company_replication,
            self.security_company_replication,
            self.commercial_policy_replication,
        )

    def install_triggers_rejecting_direct_writes_to_all_replicas(self):
        for replication in self.all_replications_with_parent_tables_first():
            replication.install_triggers_rejecting_direct_writes_to_replica()

    def refresh_all_replicas_from_reference_database(self):
        for replication in self.all_replications_with_parent_tables_first():
            replication.refresh_whole_replica_from_master()

    @subject_to_simulated_load
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

    @subject_to_simulated_load(touches_reference_data=True)
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

    @subject_to_simulated_load(touches_reference_data=True)
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

    @subject_to_simulated_load
    def update_customer(self, customer_id, **changed_column_values):
        return self.customer_replication.update_master_record_and_replicate(customer_id, **changed_column_values)

    @subject_to_simulated_load
    def update_institutional_customer(self, customer_id, **changed_column_values):
        return self.institutional_customer_replication.update_master_record_and_replicate(
            customer_id, **changed_column_values
        )

    @subject_to_simulated_load
    def add_company(self, name, company_type, tax_id, address):
        def insert_company_and_replicate_to_every_replica(transaction):
            company_id = self.company_replication.insert_into_master_and_replicate_within_transaction(
                transaction,
                name=name,
                company_type=CompanyType(company_type).value,
                tax_id=tax_id,
                address=address,
            )
            self.security_company_replication.copy_master_record_to_replica_within_transaction(transaction, company_id)
            return company_id

        return self.reference_companies.find_record_by_id(
            self.connection.run_in_single_transaction(insert_company_and_replicate_to_every_replica)
        )

    @subject_to_simulated_load
    def update_company(self, company_id, **changed_column_values):
        def update_company_and_replicate_to_every_replica(transaction):
            self.company_replication.update_master_record_and_replicate_within_transaction(
                transaction, company_id, **changed_column_values
            )
            self.security_company_replication.copy_master_record_to_replica_within_transaction(transaction, company_id)

        self.connection.run_in_single_transaction(update_company_and_replicate_to_every_replica)
        return self.reference_companies.find_record_by_id(company_id)

    @subject_to_simulated_load
    def update_commercial_policy(self, commercial_policy_id, **changed_column_values):
        return self.commercial_policy_replication.update_master_record_and_replicate(
            commercial_policy_id, **changed_column_values
        )

    def find_table(self, database_name, table_name):
        for table in self.all_tables():
            if table.database_name == database_name and table.table_name == table_name:
                return table
        raise TableNotFoundError(f"Table '{database_name}.{table_name}' does not exist")

    @subject_to_simulated_load
    def describe_first_page_of_all_tables(self, page_size):
        return [table.describe_page(1, page_size) for table in self.all_tables()]

    def _build_table(self, database_name, table_name, record_type, relationships=(), **table_options):
        return SqlTable(
            self.connection,
            database_name,
            table_name,
            record_type,
            relationships,
            simulated_load=self.simulated_load,
            touches_reference_data=database_name == self.reference_database_name
            or any(relationship.related_table.touches_reference_data for relationship in relationships),
            **table_options,
        )

    def _build_replication(self, master_table, replica_table):
        return ReplicatedReferenceTable(
            self.connection, master_table, replica_table, self.replication_guard_table_name, self.simulated_load
        )

    def _build_replica_of(self, master_table, replica_database_name):
        return self._build_table(
            replica_database_name,
            master_table.table_name,
            master_table.record_type,
            replica_of_qualified_table_name=master_table.qualified_table_name,
            primary_key_column_name=master_table.primary_key_column_name,
        )
