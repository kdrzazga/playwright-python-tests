from dash import Dash

from dealership_analytics.callbacks import DashboardCallbacks
from dealership_analytics.layout import DashboardLayoutBuilder


class DealershipAnalyticsDashboard:
    def __init__(
        self,
        repository,
        snapshot_provider,
        figure_factory,
        assets_directory,
        refresh_interval_seconds,
        title="Dealership Analytics",
    ):
        self.app = Dash(
            __name__,
            title=title,
            assets_folder=str(assets_directory),
            suppress_callback_exceptions=True,
        )
        self.app.layout = DashboardLayoutBuilder(repository, snapshot_provider, refresh_interval_seconds).build_layout
        DashboardCallbacks(self.app, repository, figure_factory, snapshot_provider).register_all()

    def run(self, host, port, debug):
        self.app.run(host=host, port=port, debug=debug)
