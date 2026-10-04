import argparse
from pathlib import Path

from application import CarDealerApplication
from http_handler import CarDealerHttpServer


class CarDealerServerLauncher:
    def __init__(self, host, port, front_end_directory):
        self.host = host
        self.port = port
        self.front_end_directory = front_end_directory

    def start_serving_until_interrupted(self):
        application = CarDealerApplication.create_with_default_users_and_demo_data(self.front_end_directory)
        with CarDealerHttpServer((self.host, self.port), application) as http_server:
            print(f"Car sales and rental app running at http://{self.host}:{self.port}/login_page.html")
            try:
                http_server.serve_forever()
            except KeyboardInterrupt:
                print("Server stopped")


def parse_command_line_arguments():
    default_front_end_directory = Path(__file__).resolve().parent.parent / "fe"
    argument_parser = argparse.ArgumentParser(description="Car sales and rental app server")
    argument_parser.add_argument("--host", default="127.0.0.1")
    argument_parser.add_argument("--port", type=int, default=8000)
    argument_parser.add_argument("--front-end-directory", type=Path, default=default_front_end_directory)
    return argument_parser.parse_args()


if __name__ == "__main__":
    arguments = parse_command_line_arguments()
    CarDealerServerLauncher(arguments.host, arguments.port, arguments.front_end_directory).start_serving_until_interrupted()
