import argparse
from datetime import date
from pathlib import Path

from dealership_analytics.analytics_repository import DealershipAnalyticsRepository
from dealership_analytics.aut1_database_loader import Aut1DatabaseLoader
from dealership_analytics.dashboard_application import DealershipAnalyticsDashboard
from dealership_analytics.figures import DashboardFigureFactory


class DealershipAnalyticsLauncher:
    def __init__(self, host, port, aut1_backend_directory, aut1_sql_directory, as_of_date, debug):
        self.host = host
        self.port = port
        self.aut1_backend_directory = aut1_backend_directory
        self.aut1_sql_directory = aut1_sql_directory
        self.as_of_date = as_of_date
        self.debug = debug
        self.assets_directory = Path(__file__).resolve().parent / "assets"

    def start_serving_until_interrupted(self):
        database = Aut1DatabaseLoader(self.aut1_backend_directory, self.aut1_sql_directory).load_database()
        dashboard = DealershipAnalyticsDashboard(
            DealershipAnalyticsRepository(database, self.as_of_date),
            DashboardFigureFactory(),
            self.assets_directory,
        )
        print(f"Dealership analytics running at http://{self.host}:{self.port}/ (data as of {self.as_of_date.isoformat()})")
        dashboard.run(self.host, self.port, self.debug)


def parse_command_line_arguments():
    repository_directory = Path(__file__).resolve().parent.parent
    argument_parser = argparse.ArgumentParser(description="Dealership analytics dashboard (AUT2)")
    argument_parser.add_argument("--host", default="127.0.0.1")
    argument_parser.add_argument("--port", type=int, default=8050)
    argument_parser.add_argument(
        "--aut1-backend-directory",
        type=Path,
        default=repository_directory / "AUT1" / "be",
        help="AUT1 backend directory whose data layer builds the database",
    )
    argument_parser.add_argument(
        "--aut1-sql-directory",
        type=Path,
        default=repository_directory / "AUT1" / "be" / "sql",
        help="AUT1 SQL directory with reference/, dealership/ and security/ scripts",
    )
    argument_parser.add_argument(
        "--as-of-date",
        type=date.fromisoformat,
        default=date.today(),
        help="Date used for vehicle status and the end of date ranges, YYYY-MM-DD (default: today)",
    )
    argument_parser.add_argument("--debug", action="store_true", help="Run Dash in debug mode with hot reload")
    return argument_parser.parse_args()


if __name__ == "__main__":
    arguments = parse_command_line_arguments()
    DealershipAnalyticsLauncher(
        arguments.host,
        arguments.port,
        arguments.aut1_backend_directory,
        arguments.aut1_sql_directory,
        arguments.as_of_date,
        arguments.debug,
    ).start_serving_until_interrupted()
