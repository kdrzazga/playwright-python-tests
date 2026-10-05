import argparse
import os
from datetime import date
from pathlib import Path

from dealership_analytics.analytics_repository import DealershipAnalyticsRepository
from dealership_analytics.aut1_api_client import Aut1ApiClient
from dealership_analytics.dashboard_application import DealershipAnalyticsDashboard
from dealership_analytics.figures import DashboardFigureFactory
from dealership_analytics.live_snapshot import LiveAut1SnapshotProvider


class DealershipAnalyticsLauncher:
    def __init__(self, host, port, aut1_url, aut1_username, aut1_password, refresh_interval_seconds, as_of_date, debug):
        self.host = host
        self.port = port
        self.aut1_url = aut1_url
        self.aut1_username = aut1_username
        self.aut1_password = aut1_password
        self.refresh_interval_seconds = refresh_interval_seconds
        self.as_of_date = as_of_date
        self.debug = debug
        self.assets_directory = Path(__file__).resolve().parent / "assets"

    def start_serving_until_interrupted(self):
        snapshot_provider = LiveAut1SnapshotProvider(Aut1ApiClient(self.aut1_url, self.aut1_username, self.aut1_password))
        dashboard = DealershipAnalyticsDashboard(
            DealershipAnalyticsRepository(snapshot_provider, self.as_of_date),
            snapshot_provider,
            DashboardFigureFactory(),
            self.assets_directory,
            self.refresh_interval_seconds,
        )
        print(
            f"Dealership analytics running at http://{self.host}:{self.port}/ "
            f"(live data from AUT1 at {self.aut1_url} as '{self.aut1_username}', refreshed every "
            f"{self.refresh_interval_seconds} s, data as of {self.as_of_date.isoformat()})"
        )
        dashboard.run(self.host, self.port, self.debug)


def parse_command_line_arguments():
    argument_parser = argparse.ArgumentParser(description="Dealership analytics dashboard (AUT2), live data from AUT1")
    argument_parser.add_argument("--host", default="127.0.0.1")
    argument_parser.add_argument("--port", type=int, default=8050)
    argument_parser.add_argument("--aut1-url", default="http://127.0.0.1:8000", help="Base URL of the running AUT1 server")
    argument_parser.add_argument(
        "--aut1-username",
        default=os.environ.get("AUT1_USERNAME", "admin"),
        help="AUT1 user with the view_db_tables permission (default: $AUT1_USERNAME or admin)",
    )
    argument_parser.add_argument(
        "--aut1-password",
        default=os.environ.get("AUT1_PASSWORD", "admin"),
        help="Password of that user (default: $AUT1_PASSWORD or admin)",
    )
    argument_parser.add_argument(
        "--refresh-seconds", type=int, default=10, help="How often the dashboard refetches data from AUT1"
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
        arguments.aut1_url,
        arguments.aut1_username,
        arguments.aut1_password,
        arguments.refresh_seconds,
        arguments.as_of_date,
        arguments.debug,
    ).start_serving_until_interrupted()
