const MAX_EVENTS = 100;
const MAX_ALERTS = 20;
const MAX_CHART_POINTS = 30;

const eventsBody = document.getElementById("events-body");
const alertsList = document.getElementById("alerts-list");
const events = [];
const alerts = [];
let totalErrors = 0;
let chart;

function showView(name, focusPanel = false) {
	for (const tab of document.querySelectorAll(".nav-tab")) {
		const selected = tab.dataset.view === name;
		tab.classList.toggle("active", selected);
		tab.setAttribute("aria-selected", String(selected));
		tab.tabIndex = selected ? 0 : -1;
	}
	for (const panel of document.querySelectorAll(".view-panel")) {
		const visible = panel.id === `view-${name}`;
		panel.hidden = !visible;
		panel.classList.toggle("active", visible);
		if (visible && focusPanel) panel.focus();
	}
	if (name === "overview" && chart) chart.resize();
}

function applyEventFilters() {
	const query = document.getElementById("event-search").value.trim().toLowerCase();
	const level = document.getElementById("level-filter").value;
	let visible = 0;
	for (const row of events) {
		const matchesLevel = level === "all" || row.dataset.level === level;
		const matchesQuery = !query || row.dataset.search.includes(query);
		row.hidden = !matchesLevel || !matchesQuery;
		if (!row.hidden) visible += 1;
	}
	const suffix = visible === 1 ? "event" : "events";
	document.getElementById("visible-events").textContent = `Showing ${visible} ${suffix}`;
	const filterEmpty = document.getElementById("events-filter-empty");
	if (filterEmpty) filterEmpty.hidden = events.length === 0 || visible > 0;
}

for (const tab of document.querySelectorAll(".nav-tab")) {
	tab.addEventListener("click", () => showView(tab.dataset.view));
	tab.addEventListener("keydown", (event) => {
		if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
		event.preventDefault();
		const tabs = [...document.querySelectorAll(".nav-tab")];
		const index = tabs.indexOf(tab);
		const nextIndex = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (index + (event.key === "ArrowDown" ? 1 : tabs.length - 1)) % tabs.length;
		tabs[nextIndex].focus();
		tabs[nextIndex].click();
	});
}

for (const button of document.querySelectorAll("[data-open-view]")) {
	button.addEventListener("click", () => showView(button.dataset.openView, true));
}

document.getElementById("event-search").addEventListener("input", applyEventFilters);
document.getElementById("level-filter").addEventListener("change", applyEventFilters);

const severityClass = (severity) => String(severity || "LOW").toLowerCase();
const levelClass = (level) => String(level || "INFO").toLowerCase();

function formatTime(timestamp) {
	const date = new Date(timestamp);
	if (Number.isNaN(date.getTime())) return String(timestamp || "—");
	return date.toLocaleTimeString([], { hour12: false });
}

function formatPercent(value) {
	return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

function setConnectionState(state, label) {
	const status = document.getElementById("connection-status");
	status.className = `connection-status ${state}`;
	document.getElementById("connection-label").textContent = label;
}

function initializeChart() {
	if (typeof Chart === "undefined") {
		document.querySelector(".chart-wrap").textContent = "Chart.js could not be loaded. Check your internet connection.";
		return;
	}

	const context = document.getElementById("error-rate-chart").getContext("2d");
	chart = new Chart(context, {
		type: "line",
		data: {
			labels: [],
			datasets: [
				{
					label: "Error rate",
					data: [],
					borderColor: "#3c7854",
					backgroundColor: "rgba(60, 120, 84, 0.10)",
					borderWidth: 2,
					pointRadius: 2,
					pointHoverRadius: 4,
					fill: true,
					tension: 0.32,
				},
				{
					label: "Baseline",
					data: [],
					borderColor: "#c66b50",
					borderWidth: 1.5,
					borderDash: [5, 5],
					pointRadius: 0,
					tension: 0,
				},
			],
		},
		options: {
			responsive: true,
			maintainAspectRatio: false,
			animation: { duration: 250 },
			interaction: { intersect: false, mode: "index" },
			plugins: {
				legend: { display: false },
				tooltip: { callbacks: { label: (item) => `${item.dataset.label}: ${formatPercent(item.raw)}` } },
			},
			scales: {
				x: {
					grid: { display: false },
					ticks: { color: "#777c70", maxTicksLimit: 7, maxRotation: 0, font: { size: 9 } },
					border: { color: "#e5e4db" },
				},
				y: {
					beginAtZero: true,
					suggestedMax: 0.1,
					grid: { color: "rgba(119, 124, 112, 0.14)" },
					ticks: { color: "#777c70", font: { size: 9 }, callback: (value) => `${(value * 100).toFixed(0)}%` },
					border: { display: false },
				},
			},
		},
	});
}

function updateChart(event) {
	if (!chart) return;
	const labels = chart.data.labels;
	labels.push(formatTime(event.timestamp));
	chart.data.datasets[0].data.push(Number(event.error_rate));
	chart.data.datasets[1].data.push(Number(event.baseline));
	while (labels.length > MAX_CHART_POINTS) {
		labels.shift();
		chart.data.datasets.forEach((dataset) => dataset.data.shift());
	}
	chart.update("none");
}

function makeBadge(text, className) {
	const badge = document.createElement("span");
	badge.className = className;
	badge.textContent = text;
	return badge;
}

function renderEvent(event) {
	document.getElementById("events-empty")?.remove();

	const row = document.createElement("tr");
	row.dataset.level = event.level;
	row.dataset.search = `${event.service} ${event.message} ${event.severity}`.toLowerCase();
	if (event.is_anomaly) row.classList.add("event-anomaly");

	const values = [
		{ text: formatTime(event.timestamp), className: "timestamp" },
		{ badge: event.level, className: `level-badge level-${levelClass(event.level)}` },
		{ text: event.service },
		{ text: event.message, className: "message-cell", title: event.message },
		{ text: formatPercent(event.error_rate) },
		{ text: formatPercent(event.baseline) },
		{ text: `${Number(event.deviation) >= 0 ? "+" : ""}${formatPercent(event.deviation)}` },
		{ badge: event.severity, className: `severity-badge severity-${severityClass(event.severity)}` },
	];

	for (const value of values) {
		const cell = document.createElement("td");
		if (value.className) cell.className = value.className;
		if (value.title) cell.title = value.title;
		if (value.badge) cell.append(makeBadge(value.badge, value.className));
		else cell.textContent = value.text;
		row.append(cell);
	}

	eventsBody.prepend(row);
	events.push(row);
	if (events.length > MAX_EVENTS) events.pop().remove();
	document.getElementById("nav-events-count").textContent = String(events.length);
	applyEventFilters();
}

function renderAlert(event) {
	document.getElementById("alerts-empty")?.remove();
	const card = document.createElement("article");
	card.className = `alert-card severity-${severityClass(event.severity)}`;

	const top = document.createElement("div");
	top.className = "alert-top";
	const title = document.createElement("span");
	title.className = "alert-title";
	title.textContent = `${event.severity} ANOMALY`;
	const time = document.createElement("span");
	time.className = "alert-time";
	time.textContent = formatTime(event.timestamp);
	top.append(title, time);

	const service = document.createElement("div");
	service.className = "alert-service";
	service.textContent = event.service;
	const message = document.createElement("div");
	message.className = "alert-message";
	message.textContent = event.message;
	const deviation = document.createElement("div");
	deviation.className = "alert-deviation";
	deviation.textContent = `Deviation: ${Number(event.deviation) >= 0 ? "+" : ""}${formatPercent(event.deviation)}`;

	card.append(top, service, message, deviation);
	alertsList.prepend(card);
	alerts.push(card);
	if (alerts.length > MAX_ALERTS) alerts.pop().remove();
	document.getElementById("nav-alert-count").textContent = String(alerts.length);
	document.getElementById("alert-count").textContent = `${alerts.length} ${alerts.length === 1 ? "signal" : "signals"}`;
}

function handleEvent(event) {
	if (!event || typeof event !== "object" || !("error_rate" in event)) return;

	document.getElementById("total-events").textContent = String(Number(document.getElementById("total-events").textContent) + 1);
	if (event.level === "ERROR") totalErrors += 1;
	document.getElementById("total-errors").textContent = String(totalErrors);

	if (event.is_anomaly) {
		document.getElementById("active-anomalies").textContent = String(Number(document.getElementById("active-anomalies").textContent) + 1);
		renderAlert(event);
		document.getElementById("alert-count").textContent = String(alerts.length);
	}

	document.getElementById("current-error-rate").textContent = `${formatPercent(event.error_rate).replace("%", "")}%`;
	document.getElementById("rate-caption").textContent = `Baseline ${formatPercent(event.baseline)}`;
	renderEvent(event);
	updateChart(event);
}

function connectWebSocket() {
	const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
	const socket = new WebSocket(`${protocol}//${window.location.host}/ws`);
	setConnectionState("connecting", "Connecting");

	socket.addEventListener("open", () => setConnectionState("connected", "WebSocket Connected"));
	socket.addEventListener("message", (message) => {
		try {
			handleEvent(JSON.parse(message.data));
		} catch (error) {
			console.error("Could not read event from WebSocket:", error);
		}
	});
	socket.addEventListener("close", () => {
		setConnectionState("disconnected", "WebSocket Disconnected");
		window.setTimeout(connectWebSocket, 2000);
	});
	socket.addEventListener("error", () => socket.close());
}

initializeChart();
connectWebSocket();
