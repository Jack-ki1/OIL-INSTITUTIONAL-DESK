/* Chart.js setup/update helpers + shared formatting utilities.
   Loaded first, so it also hosts the tiny util namespace used everywhere. */

window.U = {
  fmt2: (n) => (Math.round(Number(n) * 100) / 100).toFixed(2),
  pct: (n) => Math.round(Number(n) * 100),
  esc: (s) =>
    String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;"),
  timeOf: (iso) => {
    try {
      const d = new Date(iso);
      const hh = String(d.getHours()).padStart(2, "0");
      const mm = String(d.getMinutes()).padStart(2, "0");
      const ss = String(d.getSeconds()).padStart(2, "0");
      const ms = String(d.getMilliseconds()).padStart(3, "0");
      return { hms: `${hh}:${mm}:${ss}`, ms };
    } catch (e) {
      return { hms: "--:--:--", ms: "000" };
    }
  },
};

const GRID = "#1e293b";
const AXIS = "#64748b";

window.Charts = {
  _reg: {},

  priceChart(canvasId) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    const chart = new Chart(ctx, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          { label: "WTI", data: [], borderColor: "#fbbf24", borderWidth: 2, pointRadius: 0, tension: 0.25 },
          { label: "Brent", data: [], borderColor: "#38bdf8", borderWidth: 2, pointRadius: 0, tension: 0.25 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        plugins: { legend: { labels: { color: "#cbd5e1", boxWidth: 12, font: { size: 11 } } } },
        scales: {
          x: { grid: { color: GRID }, ticks: { display: false } },
          y: { grid: { color: GRID }, ticks: { color: AXIS, font: { size: 11 } } },
        },
      },
    });
    this._reg[canvasId] = chart;
    return chart;
  },

  volumeChart(canvasId) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    const chart = new Chart(ctx, {
      type: "bar",
      data: { labels: [], datasets: [{ label: "Volume", data: [], backgroundColor: [] }] },
      options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: GRID }, ticks: { display: false } },
          y: { grid: { color: GRID }, ticks: { color: AXIS, font: { size: 11 } } },
        },
      },
    });
    this._reg[canvasId] = chart;
    return chart;
  },

  latencyChart(canvasId, budget) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;
    const chart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: budget.map((b) => b.hop),
        datasets: [
          {
            label: "ms",
            data: budget.map((b) => b.ms),
            backgroundColor: budget.map((b) => (b.ms > 50 ? "#fbbf24" : "#2dd4bf")),
          },
        ],
      },
      options: {
        indexAxis: "y", responsive: true, maintainAspectRatio: false, animation: false,
        plugins: { legend: { display: false } },
        scales: {
          x: {
            type: "logarithmic", min: 0.1, max: 400,
            grid: { color: GRID }, ticks: { color: AXIS, font: { size: 11 } },
          },
          y: { grid: { color: GRID }, ticks: { color: "#94a3b8", font: { size: 10 } } },
        },
      },
    });
    this._reg[canvasId] = chart;
    return chart;
  },

  updatePrice(chart, wtiHist, brentHist) {
    if (!chart) return;
    chart.data.labels = wtiHist.map((h) => h.t);
    chart.data.datasets[0].data = wtiHist.map((h) => h.price);
    chart.data.datasets[1].data = brentHist.map((h) => h.price);
    chart.update();
  },

  updateVolume(chart, history, threshold) {
    if (!chart) return;
    const last = history.slice(-30);
    chart.data.labels = last.map((h) => h.t);
    chart.data.datasets[0].data = last.map((h) => h.volume);
    chart.data.datasets[0].backgroundColor = last.map((h) => (h.z >= threshold ? "#fbbf24" : "#334155"));
    chart.update();
  },
};
