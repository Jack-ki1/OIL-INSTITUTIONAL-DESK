/* Backtest Lab: form -> POST /api/backtest -> render real results table.
   Runs on demand (not from the SSE stream). */

window.BacktestPage = {
  init() {
    const form = document.getElementById("backtest-form");
    if (!form) return;
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      this.run();
    });
  },

  run() {
    const symbol = document.getElementById("bt-symbol").value;
    const period = document.getElementById("bt-period").value;
    const interval = document.getElementById("bt-interval").value;
    const out = document.getElementById("bt-results");
    const btn = document.getElementById("bt-run");

    out.innerHTML = `<div class="skeleton" style="height:120px"></div>`;
    btn.disabled = true;

    fetch("/api/backtest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol, period, interval }),
    })
      .then((r) => r.json())
      .then((res) => {
        btn.disabled = false;
        if (!res.available) {
          out.innerHTML = `<div class="empty-state">Real backtest unavailable (${window.U.esc(res.error || "no data")}).
            yfinance history may be rate-limited or offline right now — try again shortly.
            The illustrative table above still shows the <em>shape</em> of a calibration report.</div>`;
          return;
        }
        const rows = (res.sessions || [])
          .map(
            (s) => `<tr>
              <td>${window.U.esc(s.session)}</td>
              <td>${s.alerts}</td>
              <td class="tone-bull">${s.followed_move}</td>
              <td class="tone-bear">${s.false_alarms}</td>
              <td class="tone-amber">${s.win_rate}</td>
              <td class="mono">${s.avg_fwd_return}</td>
            </tr>`
          )
          .join("");
        out.innerHTML = `
          <div class="badge-real" style="margin-bottom:8px">Real — computed from ${res.bars} live ${window.U.esc(res.symbol)} bars (${window.U.esc(res.period)}/${window.U.esc(res.interval)})</div>
          <div style="overflow-x:auto">
          <table>
            <thead><tr>
              <th>Session</th><th>Alerts fired</th><th>Preceded a &gt;1% move</th>
              <th>False alarms</th><th>Win rate</th><th>Avg fwd return</th>
            </tr></thead>
            <tbody class="mono">${rows || '<tr><td colspan="6" class="muted">No session met the threshold in this window.</td></tr>'}</tbody>
          </table></div>`;
      })
      .catch((e) => {
        btn.disabled = false;
        out.innerHTML = `<div class="empty-state">Request failed: ${window.U.esc(e)}</div>`;
      });
  },
};

document.addEventListener("DOMContentLoaded", () => window.BacktestPage.init());
