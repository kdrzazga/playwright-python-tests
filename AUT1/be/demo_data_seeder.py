from database import EngineType


class DemoDataSeeder:
    def __init__(
        self,
        database,
        number_of_vehicles=60,
        number_of_sold_vehicles=15,
        number_of_rented_vehicles=12,
        oldest_manufacture_year=2015,
    ):
        self.database = database
        self.number_of_vehicles = number_of_vehicles
        self.number_of_sold_vehicles = number_of_sold_vehicles
        self.number_of_rented_vehicles = number_of_rented_vehicles
        self.oldest_manufacture_year = oldest_manufacture_year
        self.vehicle_catalog = (
            ("Volkswagen", "Golf", EngineType.DIESEL),
            ("Volkswagen", "Passat", EngineType.DIESEL),
            ("Volkswagen", "Polo", EngineType.OIL),
            ("Volkswagen", "ID.3", EngineType.ELECTRIC),
            ("Volkswagen", "ID.4", EngineType.ELECTRIC),
            ("Tesla", "Model 3", EngineType.ELECTRIC),
            ("Tesla", "Model Y", EngineType.ELECTRIC),
            ("Tesla", "Model S", EngineType.ELECTRIC),
            ("Tesla", "Model X", EngineType.ELECTRIC),
            ("Toyota", "Corolla", EngineType.OIL),
            ("Skoda", "Octavia", EngineType.DIESEL),
            ("BMW", "320d", EngineType.DIESEL),
        )
        self.customer_catalog = (
            ("Anna Kowalska", "ul. Marszalkowska 10, Warsaw"),
            ("John Smith", "221B Baker Street, London"),
            ("Maria Garcia", "Calle Mayor 5, Madrid"),
            ("Hans Mueller", "Hauptstrasse 12, Berlin"),
            ("Sophie Martin", "12 Rue de Rivoli, Paris"),
            ("Luca Rossi", "Via Roma 3, Rome"),
            ("Eva Novak", "Vaclavske namesti 1, Prague"),
            ("Piotr Nowak", "ul. Florianska 7, Krakow"),
            ("Emma Johansson", "Drottninggatan 20, Stockholm"),
            ("Liam O'Brien", "14 Grafton Street, Dublin"),
            ("Olga Ivanova", "Nevsky Prospekt 30, Tallinn"),
            ("Tomas Horvat", "Ilica 15, Zagreb"),
        )

    def seed_database_with_demo_data(self):
        self._seed_vehicles()
        self._seed_customers()
        self._seed_sales_of_first_vehicles()
        self._seed_rentals_of_vehicles_following_sold_ones()

    def _seed_vehicles(self):
        for vehicle_index in range(self.number_of_vehicles):
            brand, model, engine = self.vehicle_catalog[vehicle_index % len(self.vehicle_catalog)]
            self.database.add_vehicle(
                brand=brand,
                model=model,
                engine=engine,
                manufacture_year=self.oldest_manufacture_year + vehicle_index % 11,
                used=vehicle_index % 3 == 0,
            )

    def _seed_customers(self):
        for name, address in self.customer_catalog:
            self.database.add_customer(name=name, address=address)

    def _seed_sales_of_first_vehicles(self):
        for vehicle_id in range(1, self.number_of_sold_vehicles + 1):
            self.database.register_sale_of_vehicle_to_customer(
                vehicle_id=vehicle_id,
                customer_id=self._pick_customer_id_for_vehicle_id(vehicle_id),
            )

    def _seed_rentals_of_vehicles_following_sold_ones(self):
        first_rented_vehicle_id = self.number_of_sold_vehicles + 1
        for vehicle_id in range(first_rented_vehicle_id, first_rented_vehicle_id + self.number_of_rented_vehicles):
            self.database.register_rental_of_vehicle_to_customer(
                vehicle_id=vehicle_id,
                customer_id=self._pick_customer_id_for_vehicle_id(vehicle_id),
            )

    def _pick_customer_id_for_vehicle_id(self, vehicle_id):
        return (vehicle_id - 1) % len(self.customer_catalog) + 1
