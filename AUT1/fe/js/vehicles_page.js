import { ApiClient, ApiRequestError, PageNavigator } from "./api_client.js";
import { LogoutButton } from "./logout_button.js";
import { PaginationControls } from "./pagination_controls.js";
import { SessionFooter } from "./session_footer.js";

class MessageBanner {
    constructor() {
        this.statusMessage = document.querySelector("[data-testid='vehicle-status-message']");
        this.errorMessage = document.querySelector("[data-testid='vehicle-error-message']");
    }

    showStatus(message) {
        this.errorMessage.hidden = true;
        this.statusMessage.textContent = message;
        this.statusMessage.hidden = false;
    }

    showError(message) {
        this.statusMessage.hidden = true;
        this.errorMessage.textContent = message;
        this.errorMessage.hidden = false;
    }
}

class VehicleTableView {
    constructor(sectionElement, onPageRequested, onRemoveRequested) {
        this.sectionElement = sectionElement;
        this.onRemoveRequested = onRemoveRequested;
        this.paginationControls = new PaginationControls("vehicles", onPageRequested);
        this.userMayRemoveVehicles = false;
    }

    allowRemovingVehicles() {
        this.userMayRemoveVehicles = true;
    }

    render(vehiclePage) {
        this.sectionElement.replaceChildren(
            this.#buildShownVehicleRangeSummary(vehiclePage),
            this.#buildTableElement(vehiclePage),
            this.paginationControls.buildNavigationElement(vehiclePage.page_number, vehiclePage.total_page_count),
        );
    }

    #buildShownVehicleRangeSummary(vehiclePage) {
        const summary = document.createElement("p");
        summary.className = "record-count-summary";
        summary.dataset.testid = "vehicles-record-count";
        if (vehiclePage.records.length === 0) {
            summary.textContent = `Showing 0 of ${vehiclePage.total_record_count} vehicles`;
            return summary;
        }
        const firstShownPosition = (vehiclePage.page_number - 1) * vehiclePage.page_size + 1;
        const lastShownPosition = firstShownPosition + vehiclePage.records.length - 1;
        summary.textContent = `Showing ${firstShownPosition}–${lastShownPosition} of ${vehiclePage.total_record_count} vehicles`;
        return summary;
    }

    #buildTableElement(vehiclePage) {
        const table = document.createElement("table");
        table.dataset.testid = "vehicles-table";
        table.append(this.#buildHeaderRow(vehiclePage.column_names), this.#buildBodyWithVehicleRows(vehiclePage));
        return table;
    }

    #buildHeaderRow(columnNames) {
        const tableHead = document.createElement("thead");
        const headerRow = tableHead.insertRow();
        const headerLabels = this.userMayRemoveVehicles ? [...columnNames, "actions"] : columnNames;
        for (const headerLabel of headerLabels) {
            const headerCell = document.createElement("th");
            headerCell.textContent = headerLabel;
            headerRow.append(headerCell);
        }
        return tableHead;
    }

    #buildBodyWithVehicleRows(vehiclePage) {
        const tableBody = document.createElement("tbody");
        for (const vehicle of vehiclePage.records) {
            const vehicleRow = tableBody.insertRow();
            vehicleRow.dataset.testid = `vehicle-row-${vehicle.id}`;
            for (const columnName of vehiclePage.column_names) {
                vehicleRow.insertCell().textContent = vehicle[columnName] === null ? "" : String(vehicle[columnName]);
            }
            if (this.userMayRemoveVehicles) {
                vehicleRow.insertCell().append(this.#buildRemoveButton(vehicle));
            }
        }
        return tableBody;
    }

    #buildRemoveButton(vehicle) {
        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.className = "danger-button";
        removeButton.textContent = "Remove";
        removeButton.dataset.testid = `remove-vehicle-${vehicle.id}`;
        removeButton.addEventListener("click", () => this.onRemoveRequested(vehicle.id));
        return removeButton;
    }
}

class RandomVinGenerator {
    constructor() {
        this.allowedCharacters = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789";
        this.vinLength = 17;
    }

    generateVin() {
        const randomValues = crypto.getRandomValues(new Uint32Array(this.vinLength));
        return Array.from(randomValues, (randomValue) => this.allowedCharacters[randomValue % this.allowedCharacters.length]).join("");
    }
}

class AddVehicleForm {
    constructor(onVehicleSubmitted, vinGenerator) {
        this.onVehicleSubmitted = onVehicleSubmitted;
        this.vinGenerator = vinGenerator;
        this.section = document.querySelector("[data-testid='add-vehicle-section']");
        this.form = document.querySelector("[data-testid='add-vehicle-form']");
        this.fieldsContainer = document.querySelector("[data-testid='add-vehicle-fields']");
        this.submitButton = document.querySelector("[data-testid='add-vehicle-button']");
        this.fieldDefinitions = [
            { name: "brand", label: "Brand", kind: "choice" },
            { name: "model", label: "Model", kind: "text", defaultValue: "Demo Model" },
            { name: "engine", label: "Engine", kind: "choice", defaultValue: "electric" },
            { name: "manufacture_year", label: "Manufacture year", kind: "number", defaultValue: new Date().getFullYear() },
            { name: "used", label: "Used", kind: "checkbox", defaultValue: false },
            { name: "condition", label: "Condition", kind: "choice", defaultValue: "new" },
            { name: "body_style", label: "Body style", kind: "choice", defaultValue: "sedan" },
            { name: "transmission", label: "Transmission", kind: "choice", defaultValue: "automatic" },
            { name: "drivetrain", label: "Drivetrain", kind: "choice", defaultValue: "FWD" },
            { name: "power_hp", label: "Power (hp)", kind: "number", defaultValue: 150 },
            { name: "torque_nm", label: "Torque (Nm)", kind: "number", defaultValue: 250 },
            { name: "number_of_doors", label: "Doors", kind: "number", defaultValue: 5 },
            { name: "number_of_seats", label: "Seats", kind: "number", defaultValue: 5 },
            { name: "color", label: "Color", kind: "text", defaultValue: "White" },
            { name: "mileage_km", label: "Mileage (km)", kind: "number", defaultValue: 0 },
            { name: "vin", label: "VIN", kind: "text", defaultValue: () => this.vinGenerator.generateVin() },
            { name: "registration", label: "Registration (optional)", kind: "text", defaultValue: "" },
            { name: "price_eur", label: "Price (EUR)", kind: "number", defaultValue: 30000 },
            { name: "daily_rental_rate_eur", label: "Daily rental rate (EUR)", kind: "number", defaultValue: 60 },
        ];
        this.inputsByFieldName = new Map();
    }

    renderWithChoices(formOptions) {
        this.fieldsContainer.replaceChildren(
            ...this.fieldDefinitions.map((fieldDefinition) => this.#buildLabelledInput(fieldDefinition, formOptions)),
        );
        this.form.addEventListener("submit", (submitEvent) => {
            submitEvent.preventDefault();
            this.#submitEnteredVehicle();
        });
        this.fillWithDefaultValues();
        this.section.hidden = false;
    }

    fillWithDefaultValues() {
        for (const fieldDefinition of this.fieldDefinitions) {
            if (fieldDefinition.defaultValue === undefined) {
                continue;
            }
            const defaultValue =
                typeof fieldDefinition.defaultValue === "function" ? fieldDefinition.defaultValue() : fieldDefinition.defaultValue;
            const input = this.inputsByFieldName.get(fieldDefinition.name);
            if (fieldDefinition.kind === "checkbox") {
                input.checked = defaultValue;
            } else {
                input.value = String(defaultValue);
            }
        }
    }

    async #submitEnteredVehicle() {
        this.submitButton.disabled = true;
        try {
            const vehicleWasAdded = await this.onVehicleSubmitted(this.#readEnteredVehicleFields());
            if (vehicleWasAdded) {
                this.fillWithDefaultValues();
            }
        } finally {
            this.submitButton.disabled = false;
        }
    }

    #readEnteredVehicleFields() {
        const enteredVehicleFields = {};
        for (const fieldDefinition of this.fieldDefinitions) {
            const input = this.inputsByFieldName.get(fieldDefinition.name);
            enteredVehicleFields[fieldDefinition.name] = this.#readInputValue(fieldDefinition, input);
        }
        return enteredVehicleFields;
    }

    #readInputValue(fieldDefinition, input) {
        if (fieldDefinition.kind === "checkbox") {
            return input.checked;
        }
        if (fieldDefinition.kind === "number") {
            return input.value.trim() === "" ? null : Number(input.value);
        }
        return input.value;
    }

    #buildLabelledInput(fieldDefinition, formOptions) {
        const fieldWrapper = document.createElement("label");
        fieldWrapper.className = `vehicle-form-field vehicle-form-field-${fieldDefinition.kind}`;
        const caption = document.createElement("span");
        caption.textContent = fieldDefinition.label;
        const input = this.#buildInput(fieldDefinition, formOptions);
        input.name = fieldDefinition.name;
        input.dataset.testid = `vehicle-field-${fieldDefinition.name}`;
        this.inputsByFieldName.set(fieldDefinition.name, input);
        fieldWrapper.append(caption, input);
        return fieldWrapper;
    }

    #buildInput(fieldDefinition, formOptions) {
        if (fieldDefinition.kind === "choice") {
            const select = document.createElement("select");
            for (const choice of formOptions[fieldDefinition.name === "brand" ? "brands" : fieldDefinition.name]) {
                select.append(new Option(choice, choice));
            }
            return select;
        }
        const input = document.createElement("input");
        input.type = fieldDefinition.kind;
        if (fieldDefinition.kind === "number") {
            input.step = "1";
        }
        return input;
    }
}

class VehiclesPage {
    constructor(apiClient, pageNavigator, sessionFooter) {
        this.apiClient = apiClient;
        this.pageNavigator = pageNavigator;
        this.sessionFooter = sessionFooter;
        this.messageBanner = new MessageBanner();
        this.accessibleBrandsNotice = document.querySelector("[data-testid='accessible-brands-notice']");
        this.backToHomeButton = document.querySelector("[data-testid='back-to-home-button']");
        this.vehicleTableView = new VehicleTableView(
            document.querySelector("[data-testid='vehicles-section']"),
            (pageNumber) => this.#showPageOfVehicles(pageNumber),
            (vehicleId) => this.#removeVehicle(vehicleId),
        );
        this.addVehicleForm = new AddVehicleForm(
            (vehicleFields) => this.#addVehicle(vehicleFields),
            new RandomVinGenerator(),
        );
        this.currentPageNumber = 1;
    }

    async render() {
        this.backToHomeButton.addEventListener("click", () => this.pageNavigator.goToHomePage());
        try {
            const loggedInUser = await this.apiClient.fetchLoggedInUser();
            this.sessionFooter.renderForLoggedInUser(loggedInUser);
            this.accessibleBrandsNotice.textContent = `Brands you can access: ${loggedInUser.accessible_brands.join(", ")}`;
            if (loggedInUser.permissions.includes("vehicle.remove")) {
                this.vehicleTableView.allowRemovingVehicles();
            }
            if (loggedInUser.permissions.includes("vehicle.add")) {
                this.addVehicleForm.renderWithChoices(await this.apiClient.fetchVehicleFormOptions());
            }
            await this.#showPageOfVehicles(1);
        } catch {
            this.pageNavigator.goToLoginPage();
        }
    }

    async #showPageOfVehicles(pageNumber) {
        const vehiclePage = await this.apiClient.fetchPageOfVisibleVehicles(pageNumber);
        this.currentPageNumber = vehiclePage.page_number;
        this.vehicleTableView.render(vehiclePage);
    }

    async #addVehicle(vehicleFields) {
        try {
            const addedVehicle = await this.apiClient.addVehicle(vehicleFields);
            this.messageBanner.showStatus(`Vehicle ${addedVehicle.id} added`);
            await this.#showPageOfVehicles(this.currentPageNumber);
            return true;
        } catch (error) {
            this.#reportFailure(error);
            return false;
        }
    }

    async #removeVehicle(vehicleId) {
        try {
            await this.apiClient.removeVehicle(vehicleId);
            this.messageBanner.showStatus(`Vehicle ${vehicleId} removed`);
            await this.#showCurrentPageOrPreviousWhenCurrentBecameEmpty();
        } catch (error) {
            this.#reportFailure(error);
        }
    }

    async #showCurrentPageOrPreviousWhenCurrentBecameEmpty() {
        try {
            await this.#showPageOfVehicles(this.currentPageNumber);
        } catch (error) {
            if (error instanceof ApiRequestError && error.statusCode === 400 && this.currentPageNumber > 1) {
                await this.#showPageOfVehicles(this.currentPageNumber - 1);
                return;
            }
            throw error;
        }
    }

    #reportFailure(error) {
        if (error instanceof ApiRequestError && error.statusCode === 401) {
            this.pageNavigator.goToLoginPage();
            return;
        }
        this.messageBanner.showError(error.message);
    }
}

const apiClient = new ApiClient();
const pageNavigator = new PageNavigator();
new LogoutButton(apiClient, pageNavigator).startListeningForClicks();
new VehiclesPage(apiClient, pageNavigator, new SessionFooter()).render();
