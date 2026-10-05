export class PaginationControls {
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
