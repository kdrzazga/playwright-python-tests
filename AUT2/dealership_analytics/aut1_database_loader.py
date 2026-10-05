import importlib
import sys
from pathlib import Path


class Aut1DatabaseLoader:
    def __init__(self, aut1_backend_directory, aut1_sql_directory):
        self.aut1_backend_directory = Path(aut1_backend_directory).resolve()
        self.aut1_sql_directory = Path(aut1_sql_directory).resolve()

    def load_database(self):
        if str(self.aut1_backend_directory) not in sys.path:
            sys.path.insert(0, str(self.aut1_backend_directory))
        aut1_database_module = importlib.import_module("database")
        return aut1_database_module.InMemoryDatabase.create_from_sql_scripts_in_directory(self.aut1_sql_directory)
