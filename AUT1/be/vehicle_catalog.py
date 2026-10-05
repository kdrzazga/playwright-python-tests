from dataclasses import fields

from database_errors import IntegrityConstraintViolationError
from orm import ColumnValueInListFilter
from records import BodyStyle, Drivetrain, EngineType, PermissionName, Transmission, Vehicle, VehicleCondition


class VehicleActionNotPermittedError(Exception):
    pass


class VehicleNotVisibleError(LookupError):
    pass


class InvalidVehicleDataError(ValueError):
    pass


class VehicleStillReferencedError(Exception):
    pass


class VehicleCatalog:
    def __init__(self, database, records_per_page):
        self.database = database
        self.records_per_page = records_per_page
        self.choice_fields = {
            "engine": EngineType,
            "body_style": BodyStyle,
            "transmission": Transmission,
            "drivetrain": Drivetrain,
            "condition": VehicleCondition,
        }
        self.whole_number_fields = (
            "manufacture_year",
            "power_hp",
            "torque_nm",
            "number_of_doors",
            "number_of_seats",
            "mileage_km",
            "price_eur",
            "daily_rental_rate_eur",
        )
        self.optional_text_fields = ("registration",)
        self.boolean_fields = ("used",)

    def describe_page_of_vehicles_visible_to(self, user, page_number):
        self._ensure_user_holds_permission(user, PermissionName.VEHICLE_VIEW)
        vehicle_page = self.database.vehicles.describe_page(
            page_number, self.records_per_page, self._build_filter_of_brands_visible_to(user)
        )
        return {**vehicle_page, "accessible_brands": sorted(user.accessible_brand_names)}

    def describe_form_options_for(self, user):
        self._ensure_user_holds_permission(user, PermissionName.VEHICLE_ADD)
        return {
            "brands": sorted(user.accessible_brand_names),
            **{field_name: [choice.value for choice in choice_type] for field_name, choice_type in self.choice_fields.items()},
        }

    def add_vehicle_for(self, user, submitted_vehicle_fields):
        self._ensure_user_holds_permission(user, PermissionName.VEHICLE_ADD)
        vehicle_fields = self._parse_submitted_vehicle_fields(submitted_vehicle_fields)
        if not user.has_access_to_brand(vehicle_fields["brand"]):
            raise VehicleActionNotPermittedError(
                f"User '{user.username}' has no access to brand '{vehicle_fields['brand']}'"
            )
        try:
            added_vehicle = self.database.add_vehicle(**vehicle_fields)
        except IntegrityConstraintViolationError as error:
            raise InvalidVehicleDataError(f"Vehicle data rejected by the database: {error}") from error
        return self.database.vehicles.describe_record_with_related_records(added_vehicle)

    def remove_vehicle_for(self, user, vehicle_id):
        self._ensure_user_holds_permission(user, PermissionName.VEHICLE_REMOVE)
        vehicle = self.database.vehicles.find_record_by_id(vehicle_id)
        if vehicle is None or not user.has_access_to_brand(vehicle.brand):
            raise VehicleNotVisibleError(f"No vehicle with id {vehicle_id}")
        try:
            self.database.vehicles.delete_record_by_primary_key(vehicle_id)
        except IntegrityConstraintViolationError as error:
            raise VehicleStillReferencedError(
                f"Vehicle {vehicle_id} is part of a sale or rental and cannot be removed"
            ) from error

    @staticmethod
    def _ensure_user_holds_permission(user, permission_name):
        if not user.has_permission(permission_name):
            raise VehicleActionNotPermittedError(f"User '{user.username}' lacks permission '{permission_name}'")

    @staticmethod
    def _build_filter_of_brands_visible_to(user):
        return ColumnValueInListFilter("brand", sorted(user.accessible_brand_names))

    def _parse_submitted_vehicle_fields(self, submitted_vehicle_fields):
        expected_field_names = [vehicle_field.name for vehicle_field in fields(Vehicle) if vehicle_field.name != "id"]
        missing_field_names = [
            field_name
            for field_name in expected_field_names
            if field_name not in submitted_vehicle_fields and field_name not in self.optional_text_fields
        ]
        if missing_field_names:
            raise InvalidVehicleDataError(f"Missing fields: {', '.join(missing_field_names)}")
        return {
            field_name: self._parse_single_field(field_name, submitted_vehicle_fields.get(field_name))
            for field_name in expected_field_names
        }

    def _parse_single_field(self, field_name, submitted_value):
        if field_name in self.choice_fields:
            return self._parse_choice(field_name, submitted_value)
        if field_name in self.whole_number_fields:
            return self._parse_whole_number(field_name, submitted_value)
        if field_name in self.boolean_fields:
            return self._parse_boolean(field_name, submitted_value)
        if field_name in self.optional_text_fields:
            return self._parse_optional_text(submitted_value)
        return self._parse_required_text(field_name, submitted_value)

    def _parse_choice(self, field_name, submitted_value):
        choice_type = self.choice_fields[field_name]
        try:
            return choice_type(submitted_value).value
        except ValueError as error:
            allowed_values = ", ".join(choice.value for choice in choice_type)
            raise InvalidVehicleDataError(f"Field '{field_name}' must be one of: {allowed_values}") from error

    @staticmethod
    def _parse_whole_number(field_name, submitted_value):
        if isinstance(submitted_value, bool):
            raise InvalidVehicleDataError(f"Field '{field_name}' must be a whole number")
        try:
            return int(submitted_value)
        except (TypeError, ValueError) as error:
            raise InvalidVehicleDataError(f"Field '{field_name}' must be a whole number") from error

    @staticmethod
    def _parse_boolean(field_name, submitted_value):
        if not isinstance(submitted_value, bool):
            raise InvalidVehicleDataError(f"Field '{field_name}' must be true or false")
        return submitted_value

    @staticmethod
    def _parse_optional_text(submitted_value):
        if submitted_value is None or str(submitted_value).strip() == "":
            return None
        return str(submitted_value).strip()

    @staticmethod
    def _parse_required_text(field_name, submitted_value):
        if submitted_value is None or str(submitted_value).strip() == "":
            raise InvalidVehicleDataError(f"Field '{field_name}' must not be empty")
        return str(submitted_value).strip()
