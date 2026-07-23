/* Alert Center interactivity: threshold/cooldown sliders, require-news toggle,
   per-channel test buttons, live cooldown countdown, and the SQLite-backed
   alert log table. */

window.AlertsPage = {
  lastAlertTick: -1,

  init() {
    const zSlider = document.getElementById("z-slider");
    if (!zSlider) return; // not on the alerts page

    const cfg = window.APP_CONFIG || {};
    const zVal = document.getElementById("z-val");
    const cdSlider = document.getElementById("cd-slider");
    const cdVal = document.getElementById("cd-val");
    const newsBtn = document.getElementById("news-toggle");

    zSlider.value = cfg.z_threshold;
    zVal.textContent = `${Number(cfg.z_threshold).toFixed(1)}σ`;
    cdSlider.value = cfg.cooldown_seconds;
    cdVal.textContent = `${cfg.cooldown_seconds}s`;
    this._setNewsBtn(newsBtn, cfg.require_news);

    const post = (payload) =>
      fetch("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

    zSlider.addEventListener("input", () => {
      zVal.textContent = `${Number(zSlider.value).toFixed(1)}σ`;
    });
    zSlider.addEventListener("change", () => post({ z_threshold: parseFloat(zSlider.value) }));

    cdSlider.addEventListener("input", () => {
      cdVal.textContent = `${cdSlider.value}s`;
    });
    cdSlider.addEventListener("change", () => post({ cooldown_seconds: parseInt(cdSlider.value, 10) }));

    newsBtn.addEventListener("click", () => {
      const next = newsBtn.dataset.on !== "true";
      this._setNewsBtn(newsBtn, next);
      post({ require_news: next });
    });

    document.querySelectorAll("[data-test-channel]").forEach((btn) => {
      btn.addEventListener("click", () => this._testChannel(btn));
    });

    this.refreshLog();
  },

  _setNewsBtn(btn, on) {
    btn.dataset.on = on ? "true" : "false";
    btn.textContent = on ? "On — 3rd factor required" : "Off — 2-factor only";
    btn.classList.toggle("teal", true);
    btn.classList.toggle("active", !!on);
  },

  _testChannel(btn) {
    const channel = btn.dataset.testChannel;
    const status = document.getElementById(`test-status-${channel}`);
    status.textContent = "sending…";
    fetch("/api/test-alert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ channel }),
    })
      .then((r) => r.json())
      .then((res) => {
        status.textContent = res.ok ? "sent ✓" : `failed: ${res.error || "error"}`;
        status.className = res.ok ? "tiny tone-bull" : "tiny tone-bear";
      })
      .catch((e) => {
        status.textContent = `failed: ${e}`;
        status.className = "tiny tone-bear";
      });
  },

  refreshLog() {
    const tbody = document.getElementById("alert-log");
    if (!tbody) return;
    fetch("/api/alerts")
      .then((r) => r.json())
      .then((data) => {
        const alerts = data.alerts || [];
        if (!alerts.length) {
          tbody.innerHTML = `<div class="empty-state">No multi-factor alerts fired yet — waiting for volume + order-flow (+ news) to align.</div>`;
          return;
        }
        tbody.innerHTML = alerts
          .map((a) => {
            const dirClass = a.direction === "long" ? "tone-bull" : "tone-bear";
            const dirLabel = a.direction === "long" ? "▲ Bullish" : "▼ Bearish";
            const t = window.U.timeOf(a.ts).hms;
            const factors = (a.factors || [])
              .map((f) => {
                const cls = f.met === true ? "met" : f.met === false ? "unmet" : "na";
                const mark = f.met === null ? "n/a" : f.met ? "✓" : "✗";
                return `<span class="factor ${cls}">${window.U.esc(f.label)}: ${mark} (${window.U.esc(f.detail)})</span>`;
              })
              .join("");
            return `
            <div class="alert-card">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                <span class="${dirClass}" style="font-weight:600">${dirLabel} signal — ${window.U.esc(a.session)} session</span>
                <span class="mono tiny muted">${t}</span>
              </div>
              <div>${factors}</div>
            </div>`;
          })
          .join("");
      });
  },

  update(snapshot) {
    // cooldown countdown + suppressed count
    const cd = document.getElementById("cooldown-note");
    if (cd) {
      const remaining = snapshot.cooldown_remaining || 0;
      if (remaining > 0) {
        cd.classList.remove("hidden");
        const n = snapshot.suppressed_count || 0;
        cd.textContent = `⏱ Cooldown active — suppressing new alerts for ${remaining}s (${n} qualifying signal${n === 1 ? "" : "s"} suppressed so far this session)`;
      } else {
        cd.classList.add("hidden");
      }
    }
    // refresh the log when a new alert has just fired
    if (snapshot.alert_fired) {
      this.refreshLog();
    }
  },
};

document.addEventListener("DOMContentLoaded", () => window.AlertsPage.init());
window.updateAlerts = (s) => window.AlertsPage.update(s);
