import { ApiClient, PageNavigator } from "./api_client.js";
import { LogoutButton } from "./logout_button.js";

class PaginationControls {
    constructor(tableName, onPageRequested) {
        this.tableName = tableName;
        this.onPageRequested = onPageRequested;
    }

    buildNavigationElement(pageNumber, totalPageCount) {
        const navigation = document.createElement("nav");
        navigation.className = "pagination-controls";
        navigation.dataset.testid = `pagination-${this.tableName}`;
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
        button.dataset.testid = `pagination-${buttonRole}-${this.tableName}`;
        button.addEventListener("click", () => this.onPageRequested(targetPageNumber));
        return button;
    }

    #buildPageIndicator(pageNumber, totalPageCount) {
        const pageIndicator = document.createElement("span");
        pageIndicator.className = "page-indicator";
        pageIndicator.dataset.testid = `pagination-page-indicator-${this.tableName}`;
        pageIndicator.textContent = `Page ${pageNumber} of ${totalPageCount}`;
        return pageIndicator;
    }
}

class DatabaseTableView {
    constructor(apiClient, pageNavigator, initialTableDescription) {
        this.apiClient = apiClient;
        this.pageNavigator = pageNavigator;
        this.tableName = initialTableDescription.table_name;
        this.paginationControls = new PaginationControls(this.tableName, (pageNumber) => this.#showPage(pageNumber));
        this.sectionElement = document.createElement("section");
        this.sectionElement.className = "database-table-section";
        this.sectionElement.dataset.testid = `table-section-${this.tableName}`;
        this.#renderTablePage(initialTableDescription);
    }

    async #showPage(pageNumber) {
        try {
            const tablePage = await this.apiClient.fetchPageOfTable(this.tableName, pageNumber);
            this.#renderTablePage(tablePage);
        } catch {
            this.pageNavigator.goToLoginPage();
        }
    }

    #renderTablePage(tablePage) {
        this.sectionElement.replaceChildren(
            this.#buildHeading(),
            this.#buildShownRecordRangeSummary(tablePage),
            this.#buildTableElement(tablePage),
            this.paginationControls.buildNavigationElement(tablePage.page_number, tablePage.total_page_count),
        );
    }

    #buildHeading() {
        const heading = document.createElement("h2");
        heading.textContent = this.tableName;
        heading.dataset.testid = `table-heading-${this.tableName}`;
        return heading;
    }

    #buildShownRecordRangeSummary(tablePage) {
        const summary = document.createElement("p");
        summary.className = "record-count-summary";
        summary.dataset.testid = `record-count-${this.tableName}`;
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
        table.dataset.testid = `table-${this.tableName}`;
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
            recordRow.dataset.testid = `row-${this.tableName}-${record.id}`;
            for (const columnName of tablePage.column_names) {
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

    async renderFirstPageOfAllTables() {
        this.backToHomeButton.addEventListener("click", () => this.pageNavigator.goToHomePage());
        try {
            const databaseDescription = await this.apiClient.fetchFirstPageOfAllTables();
            this.recordLimitNotice.textContent = `${databaseDescription.records_per_page} records are shown per page`;
            const tableSections = databaseDescription.tables.map(
                (tableDescription) => new DatabaseTableView(this.apiClient, this.pageNavigator, tableDescription).sectionElement,
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
new DatabasePage(apiClient, pageNavigator).renderFirstPageOfAllTables();
