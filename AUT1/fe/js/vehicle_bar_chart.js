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
    constructor(chartContainer, chartedFieldName, yAxisTitle, valueUnitLabel, testIdPrefix, emptyChartMaximumValue, valueFormatter) {
        this.chartContainer = chartContainer;
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
        this.chartSvg = null;
        this.insertionMarkerLine = null;
        this.draggedBarClassName = "vehicle-bar-being-dragged";
    }

    get plotWidth() {
        return this.chartWidth - this.plotMargins.left - this.plotMargins.right;
    }

    get plotHeight() {
        return this.chartHeight - this.plotMargins.top - this.plotMargins.bottom;
    }

    get barSlotWidth() {
        return this.plotWidth / Math.max(this.minimumBarSlotCount, this.droppedVehicles.length);
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
            this.#buildInsertionMarkerLine(),
        );
        if (this.droppedVehicles.length === 0) {
            chartSvg.append(this.#buildEmptyChartHint());
        }
        this.chartContainer.dataset.barCount = String(this.droppedVehicles.length);
        this.chartContainer.replaceChildren(chartSvg);
        this.chartSvg = chartSvg;
    }

    canChartVehicle(vehicle) {
        const chartedValue = vehicle[this.chartedFieldName];
        return chartedValue !== null && Number.isFinite(Number(chartedValue)) && this.findChartedVehicleById(String(vehicle.id)) === null;
    }

    insertVehicleBar(vehicle, insertionIndex) {
        if (!this.canChartVehicle(vehicle)) {
            return false;
        }
        const boundedInsertionIndex = Math.min(this.droppedVehicles.length, Math.max(0, insertionIndex));
        this.droppedVehicles.splice(boundedInsertionIndex, 0, { ...vehicle, chartedValue: Number(vehicle[this.chartedFieldName]) });
        this.render();
        return true;
    }

    moveVehicleBar(vehicleId, insertionIndex) {
        const currentIndex = this.droppedVehicles.findIndex((droppedVehicle) => droppedVehicle.id === vehicleId);
        if (currentIndex === -1) {
            return;
        }
        const [movedVehicle] = this.droppedVehicles.splice(currentIndex, 1);
        const insertionIndexAfterRemoval = insertionIndex > currentIndex ? insertionIndex - 1 : insertionIndex;
        const boundedInsertionIndex = Math.min(this.droppedVehicles.length, Math.max(0, insertionIndexAfterRemoval));
        this.droppedVehicles.splice(boundedInsertionIndex, 0, movedVehicle);
        this.render();
    }

    removeVehicleBar(vehicleId) {
        this.droppedVehicles = this.droppedVehicles.filter((droppedVehicle) => droppedVehicle.id !== vehicleId);
        this.render();
    }

    findChartedVehicleById(vehicleIdText) {
        return this.droppedVehicles.find((droppedVehicle) => String(droppedVehicle.id) === vehicleIdText) ?? null;
    }

    findVehicleIdOfBarElement(element) {
        const barElement = element.closest("[data-vehicle-id]");
        return barElement === null ? null : barElement.getAttribute("data-vehicle-id");
    }

    findInsertionIndexAtClientPoint(clientX, clientY) {
        const screenTransform = this.chartSvg === null ? null : this.chartSvg.getScreenCTM();
        if (screenTransform === null) {
            return this.droppedVehicles.length;
        }
        const pointInChartCoordinates = new DOMPoint(clientX, clientY).matrixTransform(screenTransform.inverse());
        const barSlotsLeftOfPointer = (pointInChartCoordinates.x - this.plotMargins.left) / this.barSlotWidth;
        return Math.min(this.droppedVehicles.length, Math.max(0, Math.round(barSlotsLeftOfPointer)));
    }

    showInsertionMarker(insertionIndex) {
        const markerX = this.plotMargins.left + this.barSlotWidth * insertionIndex;
        this.insertionMarkerLine.setAttribute("x1", String(markerX));
        this.insertionMarkerLine.setAttribute("x2", String(markerX));
        this.insertionMarkerLine.setAttribute("data-insertion-index", String(insertionIndex));
        this.insertionMarkerLine.classList.add("chart-insertion-marker-visible");
    }

    hideInsertionMarker() {
        this.insertionMarkerLine.classList.remove("chart-insertion-marker-visible");
    }

    markBarAsDragged(vehicleId) {
        this.chartContainer.querySelector(`[data-vehicle-id="${vehicleId}"]`).classList.add(this.draggedBarClassName);
    }

    unmarkDraggedBars() {
        this.chartContainer.querySelectorAll(`.${this.draggedBarClassName}`).forEach((barElement) => barElement.classList.remove(this.draggedBarClassName));
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
        const barSlotWidth = this.barSlotWidth;
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

    #buildInsertionMarkerLine() {
        this.insertionMarkerLine = this.svgElementFactory.create("line", {
            x1: this.plotMargins.left,
            x2: this.plotMargins.left,
            y1: this.plotMargins.top,
            y2: this.plotMargins.top + this.plotHeight,
            class: "chart-insertion-marker",
            "data-testid": `${this.testIdPrefix}-chart-insertion-marker`,
        });
        return this.insertionMarkerLine;
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
