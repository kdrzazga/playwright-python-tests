import { ApiClient, PageNavigator } from "./api_client.js";
import { LogoutButton } from "./logout_button.js";

class DatabaseTableView {
    constructor(tableDescription) {
        this.tableDescription = tableDescription;
    }

    buildSectionElement() {
        const tableName = this.tableDescription.table_name;
        const section = document.createElement("section");
        section.className = "database-table-section";
        section.dataset.testid = `table-section-${tableName}`;
        section.append(this.#buildHeading(), this.#buildRecordCountSummary(), this.#buildTableElement());
        return section;
    }

    #buildHeading() {
        const heading = document.createElement("h2");
        heading.textContent = this.tableDescription.table_name;
        heading.dataset.testid = `table-heading-${this.tableDescription.table_name}`;
        return heading;
    }

    #buildRecordCountSummary() {
        const summary = document.createElement("p");
        summary.className = "record-count-summary";
        summary.dataset.testid = `record-count-${this.tableDescription.table_name}`;
        const shownRecordCount = this.tableDescription.records.length;
        summary.textContent = `Showing ${shownRecordCount} of ${this.tableDescription.total_record_count} records`;
        return summary;
    }

    #buildTableElement() {
        const table = document.createElement("table");
        table.dataset.testid = `table-${this.tableDescription.table_name}`;
        table.append(this.#buildHeaderRow(), this.#buildBodyWithRecordRows());
        return table;
    }

    #buildHeaderRow() {
        const tableHead = document.createElement("thead");
        const headerRow = tableHead.insertRow();
        for (const columnName of this.tableDescription.column_names) {
            const headerCell = document.createElement("th");
            headerCell.textContent = columnName;
            headerRow.append(headerCell);
        }
        return tableHead;
    }

    #buildBodyWithRecordRows() {
        const tableBody = document.createElement("tbody");
        for (const record of this.tableDescription.records) {
            const recordRow = tableBody.insertRow();
            recordRow.dataset.testid = `row-${this.tableDescription.table_name}-${record.id}`;
            for (const columnName of this.tableDescription.column_names) {
                recordRow.insertCell().textContent = String(record[columnName]);
            }
        }
        return tableBody;
    }
}

class DatabasePage {
    constructor(apiClient, pageNavigator) {
        this.apiClient = apiClient;
        this.pageNavigator = pageNavigator;
        this.tablesContainer = document.querySelector("[data-testid='tables-container']");
        this.recordLimitNotice = document.querySelector("[data-testid='record-limit-notice']");
        this.backToHomeButton = document.querySelector("[data-testid='back-to-home-button']");
    }

    async renderAllTables() {
        this.backToHomeButton.addEventListener("click", () => this.pageNavigator.goToHomePage());
        try {
            const databaseDescription = await this.apiClient.fetchAllTablesLimitedToDisplayedRecordLimit();
            this.recordLimitNotice.textContent =
                `Up to ${databaseDescription.displayed_record_limit} records are shown per table`;
            const tableSections = databaseDescription.tables.map(
                (tableDescription) => new DatabaseTableView(tableDescription).buildSectionElement(),
            );
            this.tablesContainer.replaceChildren(...tableSections);
        } catch {
            this.pageNavigator.goToLoginPage();
        }
    }
}

const apiClient = new ApiClient();
const pageNavigator = new PageNavigator();
new LogoutButton(apiClient, pageNavigator).startListeningForClicks();
new DatabasePage(apiClient, pageNavigator).renderAllTables();
