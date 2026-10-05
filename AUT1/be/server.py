import argparse
from pathlib import Path

from application import CarDealerApplication
from http_handler import CarDealerHttpServer


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
        help="Directory with reference/ and dealership/ subdirectories, each holding schema.sql and seed_data.sql",
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
