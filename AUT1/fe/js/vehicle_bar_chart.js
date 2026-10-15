export class DraggedVehicleTransfer {
    constructor() {
        this.transferMediaType = "application/x-vehicle";
        this.draggedVehicle = null;
        this.sourceChart = null;
    }

    get requiredDropEffect() {
        return this.sourceChart === null ? "copy" : "move";
    }

    beginDragFromTable(dataTransfer, vehicle) {
        this.#beginDrag(dataTransfer, vehicle, null);
    }

    beginDragFromChart(dataTransfer, vehicle, sourceChart) {
        this.#beginDrag(dataTransfer, vehicle, sourceChart);
    }

    endDrag() {
        this.draggedVehicle = null;
        this.sourceChart = null;
    }

    #beginDrag(dataTransfer, vehicle, sourceChart) {
        this.draggedVehicle = vehicle;
        this.sourceChart = sourceChart;
        const serializedVehicle = JSON.stringify(vehicle);
        dataTransfer.setData(this.transferMediaType, serializedVehicle);
        dataTransfer.setData("text/plain", serializedVehicle);
        dataTransfer.effectAllowed = this.requiredDropEffect;
    }
}

class SvgElementFactory {
    constructor() {
        this.svgNamespace = "http://www.w3.org/2000/svg";
    }

    create(tagName, attributes = {}, textContent = null) {
        const element = document.createElementNS(this.svgNamespace, tagName);
        for (const [attributeName, attributeValue] of Object.entries(attributes)) {
            element.setAttribute(attributeName, String(attributeValue));
        }
        if (textContent !== null) {
            element.textContent = textContent;
        }
        return element;
    }
}

class RoundedAxisScale {
    constructor(emptyChartMaximumValue, tickCount) {
        this.emptyChartMaximumValue = emptyChartMaximumValue;
        this.tickCount = tickCount;
    }

    computeAxisMaximum(largestValue) {
        if (largestValue <= 0) {
            return this.emptyChartMaximumValue;
        }
        const roughTickStep = largestValue / this.tickCount;
        const magnitude = 10 ** Math.floor(Math.log10(roughTickStep));
        const roundedTickStep = [1, 2, 2.5, 5, 10].map((multiplier) => multiplier * magnitude).find((step) => step >= roughTickStep);
        return roundedTickStep * this.tickCount;
    }

    computeTickValues(axisMaximum) {
        return Array.from({ length: this.tickCount + 1 }, (unused, tickIndex) => (axisMaximum / this.tickCount) * tickIndex);
    }
}

export class PlainNumberFormatter {
    formatAxisTick(value) {
        return String(Math.round(value));
    }

    formatBarValue(value) {
        return String(value);
    }

    formatFullValue(value, unitLabel) {
        return `${value} ${unitLabel}`;
    }
}

export class CompactCurrencyFormatter {
    constructor(localeName) {
        this.compactFormat = new Intl.NumberFormat(localeName, { notation: "compact", maximumFractionDigits: 1 });
        this.fullFormat = new Intl.NumberFormat(localeName, { maximumFractionDigits: 2 });
    }

    formatAxisTick(value) {
        return this.compactFormat.format(value);
    }

    formatBarValue(value) {
        return this.compactFormat.format(value);
    }

    formatFullValue(value, unitLabel) {
        return `${this.fullFormat.format(value)} ${unitLabel}`;
    }
}

export class VehicleBarChart {
    constructor(chartContainer, draggedVehicleTransfer, chartedFieldName, yAxisTitle, valueUnitLabel, testIdPrefix, emptyChartMaximumValue, valueFormatter) {
        this.chartContainer = chartContainer;
        this.draggedVehicleTransfer = draggedVehicleTransfer;
        this.chartedFieldName = chartedFieldName;
        this.yAxisTitle = yAxisTitle;
        this.valueUnitLabel = valueUnitLabel;
        this.testIdPrefix = testIdPrefix;
        this.valueFormatter = valueFormatter;
        this.chartedValueDataAttributeName = `data-${chartedFieldName.replaceAll("_", "-")}`;
        this.svgElementFactory = new SvgElementFactory();
        this.axisScale = new RoundedAxisScale(emptyChartMaximumValue, 5);
        this.chartWidth = 480;
        this.chartHeight = 340;
        this.plotMargins = { top: 24, right: 16, bottom: 48, left: 56 };
        this.minimumBarSlotCount = 8;
        this.barWidthShareOfSlot = 0.7;
        this.droppedVehicles = [];
        this.pressedBarVehicleId = null;
    }

    get plotWidth() {
        return this.chartWidth - this.plotMargins.left - this.plotMargins.right;
    }

    get plotHeight() {
        return this.chartHeight - this.plotMargins.top - this.plotMargins.bottom;
    }

    startAcceptingDroppedVehicles() {
        this.chartContainer.addEventListener("dragover", (dragEvent) => this.#allowDropOfVehicle(dragEvent));
        this.chartContainer.addEventListener("dragleave", () => this.chartContainer.classList.remove("drop-target-active"));
        this.chartContainer.addEventListener("drop", (dropEvent) => this.#addDroppedVehicle(dropEvent));
        this.chartContainer.draggable = true;
        this.chartContainer.addEventListener("pointerdown", (pointerEvent) => this.#rememberPressedBar(pointerEvent));
        this.chartContainer.addEventListener("dragstart", (dragEvent) => this.#startDraggingPressedBar(dragEvent));
        this.chartContainer.addEventListener("dragend", () => this.#finishDraggingBar());
        this.render();
    }

    addVehicleBar(vehicle) {
        const chartedValue = Number(vehicle[this.chartedFieldName]);
        if (vehicle[this.chartedFieldName] === null || !Number.isFinite(chartedValue) || this.#isVehicleAlreadyCharted(vehicle)) {
            return false;
        }
        this.droppedVehicles.push({ ...vehicle, chartedValue });
        this.render();
        return true;
    }

    removeVehicleBar(vehicleId) {
        this.droppedVehicles = this.droppedVehicles.filter((droppedVehicle) => droppedVehicle.id !== vehicleId);
        this.render();
    }

    render() {
        const chartSvg = this.svgElementFactory.create("svg", {
            viewBox: `0 0 ${this.chartWidth} ${this.chartHeight}`,
            role: "img",
            "aria-label": `${this.yAxisTitle} of dropped vehicles`,
            class: "vehicle-bar-chart-svg",
            "data-testid": `${this.testIdPrefix}-bar-chart-svg`,
        });
        const axisMaximum = this.axisScale.computeAxisMaximum(Math.max(0, ...this.droppedVehicles.map((vehicle) => vehicle.chartedValue)));
        chartSvg.append(
            this.#buildHorizontalGridAndYAxisTicks(axisMaximum),
            this.#buildBars(axisMaximum),
            this.#buildAxisLines(),
            this.#buildAxisTitles(),
        );
        if (this.droppedVehicles.length === 0) {
            chartSvg.append(this.#buildEmptyChartHint());
        }
        this.chartContainer.dataset.barCount = String(this.droppedVehicles.length);
        this.chartContainer.replaceChildren(chartSvg);
    }

    #isVehicleAlreadyCharted(vehicle) {
        return this.droppedVehicles.some((droppedVehicle) => droppedVehicle.id === vehicle.id);
    }

    #canAcceptDraggedVehicle() {
        const draggedVehicle = this.draggedVehicleTransfer.draggedVehicle;
        return draggedVehicle !== null && this.draggedVehicleTransfer.sourceChart !== this && !this.#isVehicleAlreadyCharted(draggedVehicle);
    }

    #allowDropOfVehicle(dragEvent) {
        if (!this.#canAcceptDraggedVehicle()) {
            return;
        }
        dragEvent.preventDefault();
        dragEvent.dataTransfer.dropEffect = this.draggedVehicleTransfer.requiredDropEffect;
        this.chartContainer.classList.add("drop-target-active");
    }

    #addDroppedVehicle(dropEvent) {
        dropEvent.preventDefault();
        this.chartContainer.classList.remove("drop-target-active");
        if (!this.#canAcceptDraggedVehicle()) {
            return;
        }
        const draggedVehicle = this.draggedVehicleTransfer.draggedVehicle;
        const sourceChart = this.draggedVehicleTransfer.sourceChart;
        if (this.addVehicleBar(draggedVehicle) && sourceChart !== null) {
            sourceChart.removeVehicleBar(draggedVehicle.id);
        }
        this.draggedVehicleTransfer.endDrag();
    }

    #rememberPressedBar(pointerEvent) {
        const pressedBarElement = pointerEvent.target.closest("[data-vehicle-id]");
        this.pressedBarVehicleId = pressedBarElement === null ? null : pressedBarElement.getAttribute("data-vehicle-id");
    }

    #startDraggingPressedBar(dragEvent) {
        const pressedBarVehicle = this.droppedVehicles.find((droppedVehicle) => String(droppedVehicle.id) === this.pressedBarVehicleId);
        if (pressedBarVehicle === undefined) {
            dragEvent.preventDefault();
            return;
        }
        this.draggedVehicleTransfer.beginDragFromChart(dragEvent.dataTransfer, pressedBarVehicle, this);
        this.chartContainer.querySelector(`[data-vehicle-id="${this.pressedBarVehicleId}"]`).classList.add("vehicle-bar-being-dragged");
    }

    #finishDraggingBar() {
        this.pressedBarVehicleId = null;
        this.chartContainer.querySelectorAll(".vehicle-bar-being-dragged").forEach((barElement) => barElement.classList.remove("vehicle-bar-being-dragged"));
        if (this.draggedVehicleTransfer.sourceChart === this) {
            this.draggedVehicleTransfer.endDrag();
        }
    }

    #convertValueToY(value, axisMaximum) {
        return this.plotMargins.top + this.plotHeight - (value / axisMaximum) * this.plotHeight;
    }

    #buildHorizontalGridAndYAxisTicks(axisMaximum) {
        const gridGroup = this.svgElementFactory.create("g", { class: "chart-grid", "data-testid": `${this.testIdPrefix}-chart-y-ticks` });
        for (const tickValue of this.axisScale.computeTickValues(axisMaximum)) {
            const tickY = this.#convertValueToY(tickValue, axisMaximum);
            gridGroup.append(
                this.svgElementFactory.create("line", {
                    x1: this.plotMargins.left,
                    x2: this.plotMargins.left + this.plotWidth,
                    y1: tickY,
                    y2: tickY,
                    class: "chart-grid-line",
                }),
                this.svgElementFactory.create(
                    "text",
                    { x: this.plotMargins.left - 8, y: tickY + 4, "text-anchor": "end", class: "chart-tick-label" },
                    this.valueFormatter.formatAxisTick(tickValue),
                ),
            );
        }
        return gridGroup;
    }

    #buildBars(axisMaximum) {
        const barsGroup = this.svgElementFactory.create("g", { "data-testid": `${this.testIdPrefix}-chart-bars` });
        const barSlotWidth = this.plotWidth / Math.max(this.minimumBarSlotCount, this.droppedVehicles.length);
        const barWidth = barSlotWidth * this.barWidthShareOfSlot;
        const plotBottomY = this.plotMargins.top + this.plotHeight;
        this.droppedVehicles.forEach((vehicle, barIndex) => {
            const barCenterX = this.plotMargins.left + barSlotWidth * barIndex + barSlotWidth / 2;
            const barTopY = this.#convertValueToY(vehicle.chartedValue, axisMaximum);
            const barGroup = this.svgElementFactory.create("g", {
                class: "chart-bar",
                "data-testid": `${this.testIdPrefix}-bar-${vehicle.id}`,
                "data-vehicle-id": vehicle.id,
                [this.chartedValueDataAttributeName]: vehicle.chartedValue,
            });
            barGroup.append(
                this.svgElementFactory.create(
                    "title",
                    {},
                    `ID ${vehicle.id}: ${vehicle.brand ?? ""} ${vehicle.model ?? ""} – ${this.valueFormatter.formatFullValue(vehicle.chartedValue, this.valueUnitLabel)}`,
                ),
                this.svgElementFactory.create("rect", {
                    x: barCenterX - barWidth / 2,
                    y: barTopY,
                    width: barWidth,
                    height: plotBottomY - barTopY,
                    class: "chart-bar-rect",
                }),
                this.svgElementFactory.create(
                    "text",
                    { x: barCenterX, y: barTopY - 6, "text-anchor": "middle", class: "chart-bar-value-label", "data-testid": `${this.testIdPrefix}-bar-value-${vehicle.id}` },
                    this.valueFormatter.formatBarValue(vehicle.chartedValue),
                ),
                this.svgElementFactory.create(
                    "text",
                    { x: barCenterX, y: plotBottomY + 18, "text-anchor": "middle", class: "chart-tick-label", "data-testid": `${this.testIdPrefix}-bar-label-${vehicle.id}` },
                    String(vehicle.id),
                ),
            );
            barsGroup.append(barGroup);
        });
        return barsGroup;
    }

    #buildAxisLines() {
        const plotBottomY = this.plotMargins.top + this.plotHeight;
        const axisGroup = this.svgElementFactory.create("g", { class: "chart-axis" });
        axisGroup.append(
            this.svgElementFactory.create("line", {
                x1: this.plotMargins.left,
                x2: this.plotMargins.left + this.plotWidth,
                y1: plotBottomY,
                y2: plotBottomY,
                class: "chart-axis-line",
                "data-testid": `${this.testIdPrefix}-chart-x-axis`,
            }),
            this.svgElementFactory.create("line", {
                x1: this.plotMargins.left,
                x2: this.plotMargins.left,
                y1: this.plotMargins.top,
                y2: plotBottomY,
                class: "chart-axis-line",
                "data-testid": `${this.testIdPrefix}-chart-y-axis`,
            }),
        );
        return axisGroup;
    }

    #buildAxisTitles() {
        const titlesGroup = this.svgElementFactory.create("g", { class: "chart-axis-titles" });
        const plotCenterY = this.plotMargins.top + this.plotHeight / 2;
        titlesGroup.append(
            this.svgElementFactory.create(
                "text",
                {
                    x: this.plotMargins.left + this.plotWidth / 2,
                    y: this.chartHeight - 8,
                    "text-anchor": "middle",
                    class: "chart-axis-title",
                    "data-testid": `${this.testIdPrefix}-chart-x-axis-title`,
                },
                "ID",
            ),
            this.svgElementFactory.create(
                "text",
                {
                    x: 16,
                    y: plotCenterY,
                    "text-anchor": "middle",
                    transform: `rotate(-90 16 ${plotCenterY})`,
                    class: "chart-axis-title",
                    "data-testid": `${this.testIdPrefix}-chart-y-axis-title`,
                },
                this.yAxisTitle,
            ),
        );
        return titlesGroup;
    }

    #buildEmptyChartHint() {
        return this.svgElementFactory.create(
            "text",
            {
                x: this.plotMargins.left + this.plotWidth / 2,
                y: this.plotMargins.top + this.plotHeight / 2,
                "text-anchor": "middle",
                class: "chart-empty-hint",
                "data-testid": `${this.testIdPrefix}-chart-empty-hint`,
            },
            "Drag a vehicle row or bar here",
        );
    }
}
