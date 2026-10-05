import re

from playwright.sync_api import BrowserContext, Error, Route


class PageAssetGuard:
    def __init__(self, site_base_url: str, blocked_url_patterns: tuple[str, ...], asset_timeout_ms: int) -> None:
        self.blocked_url_patterns = blocked_url_patterns
        self.asset_timeout_ms = asset_timeout_ms
        self.guarded_asset_url_pattern = re.compile(re.escape(site_base_url.rstrip("/")) + r"/.*\.(?:js|css)(?:\?.*)?$")
        self.content_types_by_asset_extension = {".js": "application/javascript", ".css": "text/css"}

    def install_on(self, context: BrowserContext) -> None:
        context.route(self.guarded_asset_url_pattern, self._serve_asset_or_empty_substitute_when_slow_or_failing)
        for blocked_url_pattern in self.blocked_url_patterns:
            context.route(blocked_url_pattern, lambda route: route.abort())

    def _serve_asset_or_empty_substitute_when_slow_or_failing(self, route: Route) -> None:
        try:
            asset_response = route.fetch(timeout=self.asset_timeout_ms)
        except Error as error:
            self._serve_empty_substitute(route, f"did not load within {self.asset_timeout_ms} ms ({error.message.splitlines()[0]})")
            return
        if asset_response.status >= 500:
            self._serve_empty_substitute(route, f"answered HTTP {asset_response.status}")
            return
        route.fulfill(response=asset_response)

    def _serve_empty_substitute(self, route: Route, reason: str) -> None:
        asset_url = route.request.url
        print(f"[page-asset-guard] {asset_url} {reason}; serving an empty substitute")
        asset_extension = ".css" if asset_url.split("?")[0].endswith(".css") else ".js"
        route.fulfill(status=200, body="", content_type=self.content_types_by_asset_extension[asset_extension])
