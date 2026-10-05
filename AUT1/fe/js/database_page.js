import { ApiClient, PageNavigator } from "./api_client.js";
import { LogoutButton } from "./logout_button.js";
import { SessionFooter } from "./session_footer.js";

class PaginationControls {
    constructor(tableKey, onPageRequested) {
        this.tableKey = tableKey;
        this.onPageRequested = onPageRequested;
    }

    buildNavigationElement(pageNumber, totalPageCount) {
        const navigation = document.createElement("nav");
        navigation.className = "pagination-controls";
        navigation.dataset.testid = `pagination-${this.tableKey}`;
        const isFirstPage = pageNumber === 1;
        const isLastPage = pageNumber === totalPageCount;
        navigation.append(
            this.#buildNavigationButton("first", "« First", 1, isFirstPage),
            this.#buildNavigationButton("previous", "‹ Previous", pageNumber - 1, isFirstPage),
            this.#buildPageIndicator(pageNumber, totalPageCount),
            this.#buildNavigationButton("next", "Next ›", pageNumber + 1, isLastPage),
            this.#buildNavigationButton("last", "Last »", totalPageCount, isLastPage),
        );
        return navigation;
    }

    #buildNavigationButton(buttonRole, buttonLabel, targetPageNumber, isDisabled) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "secondary-button";
        button.textContent = buttonLabel;
        button.disabled = isDisabled;
        button.dataset.testid = `pagination-${buttonRole}-${this.tableKey}`;
        button.addEventListener("click", () => this.onPageRequested(targetPageNumber));
        return button;
    }

    #buildPageIndicator(pageNumber, totalPageCount) {
        const pageIndicator = document.createElement("span");
        pageIndicator.className = "page-indicator";
        pageIndicator.dataset.testid = `pagination-page-indicator-${this.tableKey}`;
        pageIndicator.textContent = `Page ${pageNumber} of ${totalPageCount}`;
        return pageIndicator;
    }
}

class DatabaseTableView {
    constructor(apiClient, pageNavigator, initialTableDescription) {
        this.apiClient = apiClient;
        this.pageNavigator = pageNavigator;
        this.databaseName = initialTableDescription.database_name;
        this.tableName = initialTableDescription.table_name;
        this.replicaOf = initialTableDescription.replica_of;
        this.tableKey = `${this.databaseName}-${this.tableName}`;
        this.paginationControls = new PaginationControls(this.tableKey, (pageNumber) => this.#showPage(pageNumber));
        this.sectionElement = document.createElement("section");
        this.sectionElement.className = "database-table-section";
        this.sectionElement.dataset.testid = `table-section-${this.tableKey}`;
        this.#renderTablePage(initialTableDescription);
    }

    async #showPage(pageNumber) {
        try {
            const tablePage = await this.apiClient.fetchPageOfTable(this.databaseName, this.tableName, pageNumber);
            this.#renderTablePage(tablePage);
        } catch {
            this.pageNavigator.goToLoginPage();
        }
    }

    #renderTablePage(tablePage) {
        this.sectionElement.replaceChildren(
            this.#buildHeading(),
            ...this.#buildReplicaNoticeWhenTableIsReplica(),
            this.#buildShownRecordRangeSummary(tablePage),
            this.#buildTableElement(tablePage),
            this.paginationControls.buildNavigationElement(tablePage.page_number, tablePage.total_page_count),
        );
    }

    #buildHeading() {
        const heading = document.createElement("h3");
        heading.textContent = `${this.databaseName}.${this.tableName}`;
        heading.dataset.testid = `table-heading-${this.tableKey}`;
        return heading;
    }

    #buildReplicaNoticeWhenTableIsReplica() {
        if (this.replicaOf === null) {
            return [];
        }
        const replicaNotice = document.createElement("p");
        replicaNotice.className = "replica-notice";
        replicaNotice.dataset.testid = `replica-notice-${this.tableKey}`;
        replicaNotice.textContent = `Read-only replica of ${this.replicaOf}`;
        return [replicaNotice];
    }

    #buildShownRecordRangeSummary(tablePage) {
        const summary = document.createElement("p");
        summary.className = "record-count-summary";
        summary.dataset.testid = `record-count-${this.tableKey}`;
        summary.textContent = this.#describeShownRecordRange(tablePage);
        return summary;
    }

    #describeShownRecordRange(tablePage) {
        if (tablePage.records.length === 0) {
            return `Showing 0 of ${tablePage.total_record_count} records`;
        }
        const firstShownRecordPosition = (tablePage.page_number - 1) * tablePage.page_size + 1;
        const lastShownRecordPosition = firstShownRecordPosition + tablePage.records.length - 1;
        return `Showing ${firstShownRecordPosition}–${lastShownRecordPosition} of ${tablePage.total_record_count} records`;
    }

    #buildTableElement(tablePage) {
        const table = document.createElement("table");
        table.dataset.testid = `table-${this.tableKey}`;
        table.append(this.#buildHeaderRow(tablePage.column_names), this.#buildBodyWithRecordRows(tablePage));
        return table;
    }

    #buildHeaderRow(columnNames) {
        const tableHead = document.createElement("thead");
        const headerRow = tableHead.insertRow();
        for (const columnName of columnNames) {
            const headerCell = document.createElement("th");
            headerCell.textContent = columnName;
            headerRow.append(headerCell);
        }
        return tableHead;
    }

    #buildBodyWithRecordRows(tablePage) {
        const tableBody = document.createElement("tbody");
        for (const record of tablePage.records) {
            const recordRow = tableBody.insertRow();
            recordRow.dataset.testid = `row-${this.tableKey}-${record[tablePage.primary_key_column_name]}`;
            for (const columnName of tablePage.column_names) {
                recordRow.insertCell().textContent = this.#formatCellValue(record[columnName]);
            }
        }
        return tableBody;
    }

    #formatCellValue(cellValue) {
        return cellValue === null ? "" : String(cellValue);
    }
}

class DatabasePage {
    constructor(apiClient, pageNavigator, sessionFooter) {
        this.apiClient = apiClient;
        this.pageNavigator = pageNavigator;
        this.sessionFooter = sessionFooter;
        this.tablesContainer = document.querySelector("[data-testid='tables-container']");
        this.recordLimitNotice = document.querySelector("[data-testid='record-limit-notice']");
        this.backToHomeButton = document.querySelector("[data-testid='back-to-home-button']");
    }

    async renderFirstPageOfAllTables() {
        this.backToHomeButton.addEventListener("click", () => this.pageNavigator.goToHomePage());
        try {
            const [loggedInUser, databaseDescription] = await Promise.all([
                this.apiClient.fetchLoggedInUser(),
                this.apiClient.fetchFirstPageOfAllTables(),
            ]);
            this.sessionFooter.renderForLoggedInUser(loggedInUser);
            this.recordLimitNotice.textContent = `${databaseDescription.records_per_page} records are shown per page`;
            this.tablesContainer.replaceChildren(...this.#buildDatabaseGroups(databaseDescription.tables));
        } catch {
            this.pageNavigator.goToLoginPage();
        }
    }

    #buildDatabaseGroups(tableDescriptions) {
        const tableDescriptionsByDatabaseName = Map.groupBy(
            tableDescriptions,
            (tableDescription) => tableDescription.database_name,
        );
        return [...tableDescriptionsByDatabaseName].map(([databaseName, databaseTableDescriptions]) =>
            this.#buildDatabaseGroup(databaseName, databaseTableDescriptions),
        );
    }

    #buildDatabaseGroup(databaseName, databaseTableDescriptions) {
        const databaseGroup = document.createElement("section");
        databaseGroup.className = "database-group";
        databaseGroup.dataset.testid = `database-group-${databaseName}`;
        const databaseHeading = document.createElement("h2");
        databaseHeading.textContent = databaseName.toUpperCase();
        databaseHeading.dataset.testid = `database-heading-${databaseName}`;
        const tableSections = databaseTableDescriptions.map(
            (tableDescription) => new DatabaseTableView(this.apiClient, this.pageNavigator, tableDescription).sectionElement,
        );
        databaseGroup.append(databaseHeading, ...tableSections);
        return databaseGroup;
    }
}

const apiClient = new ApiClient();
const pageNavigator = new PageNavigator();
new LogoutButton(apiClient, pageNavigator).startListeningForClicks();
new DatabasePage(apiClient, pageNavigator, new SessionFooter()).renderFirstPageOfAllTables();
