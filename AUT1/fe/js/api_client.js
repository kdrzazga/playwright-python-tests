export class ApiRequestError extends Error {
    constructor(statusCode, message) {
        super(message);
        this.statusCode = statusCode;
    }
}

export class ApiClient {
    async logIn(username, password) {
        return this.#sendJsonRequest("POST", "/api/login", { username, password });
    }

    async logOut() {
        return this.#sendJsonRequest("POST", "/api/logout", {});
    }

    async fetchLoggedInUser() {
        return this.#sendJsonRequest("GET", "/api/session");
    }

    async fetchFirstPageOfAllTables() {
        return this.#sendJsonRequest("GET", "/api/database/tables");
    }

    async fetchPageOfTable(databaseName, tableName, pageNumber) {
        const tablePath = `${encodeURIComponent(databaseName)}/${encodeURIComponent(tableName)}`;
        const tableUrl = `/api/database/tables/${tablePath}?page=${pageNumber}`;
        return this.#sendJsonRequest("GET", tableUrl);
    }

    async fetchPageOfVisibleVehicles(pageNumber) {
        return this.#sendJsonRequest("GET", `/api/vehicles?page=${pageNumber}`);
    }

    async fetchVehicleFormOptions() {
        return this.#sendJsonRequest("GET", "/api/vehicles/form-options");
    }

    async addVehicle(vehicleFields) {
        return this.#sendJsonRequest("POST", "/api/vehicles", vehicleFields);
    }

    async removeVehicle(vehicleId) {
        return this.#sendJsonRequest("DELETE", `/api/vehicles/${vehicleId}`);
    }

    async #sendJsonRequest(method, url, requestBody) {
        const response = await fetch(url, {
            method,
            headers: requestBody === undefined ? {} : { "Content-Type": "application/json" },
            body: requestBody === undefined ? undefined : JSON.stringify(requestBody),
            credentials: "same-origin",
        });
        const responseBody = await response.json();
        if (!response.ok) {
            throw new ApiRequestError(response.status, responseBody.error ?? "Request failed");
        }
        return responseBody;
    }
}

export class PageNavigator {
    constructor() {
        this.loginPageUrl = "/login_page.html";
        this.homePageUrl = "/home_page.html";
        this.databasePageUrl = "/database_page.html";
        this.vehiclesPageUrl = "/vehicles_page.html";
    }

    goToLoginPage() {
        window.location.assign(this.loginPageUrl);
    }

    goToHomePage() {
        window.location.assign(this.homePageUrl);
    }

    goToDatabasePage() {
        window.location.assign(this.databasePageUrl);
    }

    goToVehiclesPage() {
        window.location.assign(this.vehiclesPageUrl);
    }
}
