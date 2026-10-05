import argparse
from pathlib import Path

from application import CarDealerApplication
from http_handler import CarDealerHttpServer


class AvailableUsersConsoleTable:
    def __init__(self, application):
        self.application = application
        self.column_headers = ("username", "role", "full name", "frontend", "permissions", "brands")

    def print_table(self):
        table_rows = [self._describe_user_as_row(user) for user in self.application.authentication_service.user_repository.list_all_users()]
        column_widths = [
            max(len(row[column_index]) for row in (self.column_headers, *table_rows))
            for column_index in range(len(self.column_headers))
        ]
        print("Available users:")
        print(self._format_row(self.column_headers, column_widths))
        print(self._format_row(tuple("-" * column_width for column_width in column_widths), column_widths))
        for table_row in table_rows:
            print(self._format_row(table_row, column_widths))

    def _describe_user_as_row(self, user):
        return (
            user.username,
            user.role.value,
            f"{user.name} {user.last_name}",
            "yes" if self.application.authentication_service.user_may_use_front_end(user) else "no",
            str(len(user.permissions)),
            ", ".join(sorted(user.accessible_brand_names)) or "-",
        )

    @staticmethod
    def _format_row(row_values, column_widths):
        return "  " + "  ".join(value.ljust(column_width) for value, column_width in zip(row_values, column_widths)).rstrip()


class CarDealerServerLauncher:
    def __init__(self, host, port, front_end_directory, sql_directory, extra_load_enabled):
        self.host = host
        self.port = port
        self.front_end_directory = front_end_directory
        self.sql_directory = sql_directory
        self.extra_load_enabled = extra_load_enabled

    def start_serving_until_interrupted(self):
        application = CarDealerApplication.create_with_default_users_and_database_built_from_sql_scripts(
            self.front_end_directory, self.sql_directory, self.extra_load_enabled
        )
        if self.extra_load_enabled:
            print("Extra load enabled: each reference data call rolls 3 times, ~15% chance per roll of a 2-5 second delay")
        with CarDealerHttpServer((self.host, self.port), application) as http_server:
            print(f"Car sales and rental app running at http://{self.host}:{self.port}/login_page.html")
            AvailableUsersConsoleTable(application).print_table()
            try:
                http_server.serve_forever()
            except KeyboardInterrupt:
                print("Server stopped")


def parse_command_line_arguments():
    backend_directory = Path(__file__).resolve().parent
    argument_parser = argparse.ArgumentParser(description="Car sales and rental app server")
    argument_parser.add_argument("--host", default="127.0.0.1")
    argument_parser.add_argument("--port", type=int, default=8000)
    argument_parser.add_argument("--front-end-directory", type=Path, default=backend_directory.parent / "fe")
    argument_parser.add_argument(
        "--sql-directory",
        type=Path,
        default=backend_directory / "sql",
        help="Directory with reference/, dealership/ and security/ subdirectories, each holding schema.sql and seed_data.sql",
    )
    argument_parser.add_argument(
        "--extra-load",
        "-el",
        action="store_true",
        help="Simulate heavy load: each call touching reference data rolls 3 times, ~15%% chance per roll of a 2-5 s delay",
    )
    return argument_parser.parse_args()


if __name__ == "__main__":
    arguments = parse_command_line_arguments()
    CarDealerServerLauncher(
        arguments.host, arguments.port, arguments.front_end_directory, arguments.sql_directory, arguments.extra_load
    ).start_serving_until_interrupted()
