from pathlib import Path

from authentication import AuthenticationService, SessionStore, UserRepository
from database import InMemoryDatabase
from demo_data_seeder import DemoDataSeeder


class CarDealerApplication:
    def __init__(
        self,
        database,
        authentication_service,
        front_end_directory,
        displayed_record_limit=50,
        session_cookie_name="session_token",
    ):
        self.database = database
        self.authentication_service = authentication_service
        self.front_end_directory = Path(front_end_directory).resolve()
        self.displayed_record_limit = displayed_record_limit
        self.session_cookie_name = session_cookie_name
        self.login_page_path = "/login_page.html"
        self.page_access_rules = {
            "/home_page.html": lambda user: user.can_access_front_end,
            "/database_page.html": lambda user: user.can_view_whole_database,
        }
        self.content_types_by_file_suffix = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".ico": "image/x-icon",
            ".png": "image/png",
            ".svg": "image/svg+xml",
        }

    @classmethod
    def create_with_default_users_and_demo_data(cls, front_end_directory):
        database = InMemoryDatabase()
        DemoDataSeeder(database).seed_database_with_demo_data()
        authentication_service = AuthenticationService(
            UserRepository.with_default_application_users(),
            SessionStore(),
        )
        return cls(database, authentication_service, front_end_directory)

    def is_protected_page(self, request_path):
        return request_path in self.page_access_rules

    def user_is_allowed_to_open_page(self, user, request_path):
        return user is not None and self.page_access_rules[request_path](user)

    def describe_all_tables_for_display(self):
        return {
            "displayed_record_limit": self.displayed_record_limit,
            "tables": self.database.describe_all_tables_with_records_up_to_limit(self.displayed_record_limit),
        }

    def find_front_end_file_for_request_path(self, request_path):
        candidate_file = (self.front_end_directory / request_path.lstrip("/")).resolve()
        if candidate_file.is_relative_to(self.front_end_directory) and candidate_file.is_file():
            return candidate_file
        return None

    def content_type_for_file(self, file_path):
        return self.content_types_by_file_suffix.get(file_path.suffix.lower(), "application/octet-stream")
