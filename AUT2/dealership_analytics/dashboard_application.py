from dash import Dash

from dealership_analytics.callbacks import DashboardCallbacks
from dealership_analytics.layout import DashboardLayoutBuilder


class DealershipAnalyticsDashboard:
    def __init__(self, repository, figure_factory, assets_directory, title="Dealership Analytics"):
        self.app = Dash(__name__, title=title, assets_folder=str(assets_directory))
        self.app.layout = DashboardLayoutBuilder(repository).build_layout()
        DashboardCallbacks(self.app, repository, figure_factory).register_all()

    def run(self, host, port, debug):
        self.app.run(host=host, port=port, debug=debug)
