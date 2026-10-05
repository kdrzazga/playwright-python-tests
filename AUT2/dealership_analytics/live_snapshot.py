import hashlib
import json
import threading
from dataclasses import dataclass
from datetime import datetime

from dealership_analytics.aut1_api_client import Aut1UnavailableError


@dataclass(frozen=True)
class AnalyticsSnapshot:
    vehicles: list
    sale_agreements: list
    sales: list
    rental_agreements: list
    rentals: list
    loans: list
    factories: list
    fetched_at: datetime

    def fingerprint(self):
        snapshot_content = {
            "vehicles": self.vehicles,
            "sale_agreements": self.sale_agreements,
            "sales": self.sales,
            "rental_agreements": self.rental_agreements,
            "rentals": self.rentals,
            "loans": self.loans,
            "factories": self.factories,
        }
        return hashlib.sha256(json.dumps(snapshot_content, sort_keys=True).encode()).hexdigest()


class LiveAut1SnapshotProvider:
    def __init__(self, api_client, current_time_provider=datetime.now):
        self.api_client = api_client
        self.current_time_provider = current_time_provider
        self.tables_by_snapshot_field = {
            "vehicles": ("dealership", "vehicles"),
            "sale_agreements": ("dealership", "sale_agreements"),
            "sales": ("dealership", "sales"),
            "rental_agreements": ("dealership", "rental_agreements"),
            "rentals": ("dealership", "rentals"),
            "loans": ("dealership", "loans"),
            "factories": ("reference", "factories"),
        }
        self._latest_snapshot = None
        self._latest_error = None
        self._refresh_lock = threading.Lock()

    @property
    def source_description(self):
        return self.api_client.base_url

    @property
    def latest_error(self):
        return self._latest_error

    def current_snapshot(self):
        if self._latest_snapshot is None:
            self.refresh()
        if self._latest_snapshot is None:
            raise Aut1UnavailableError(self._latest_error or "No data has been loaded from AUT1 yet")
        return self._latest_snapshot

    def refresh(self):
        with self._refresh_lock:
            try:
                self._latest_snapshot = AnalyticsSnapshot(
                    **{
                        snapshot_field: self.api_client.fetch_all_records_of_table(database_name, table_name)
                        for snapshot_field, (database_name, table_name) in self.tables_by_snapshot_field.items()
                    },
                    fetched_at=self.current_time_provider(),
                )
                self._latest_error = None
            except Aut1UnavailableError as error:
                self._latest_error = str(error)
        return self._latest_snapshot
