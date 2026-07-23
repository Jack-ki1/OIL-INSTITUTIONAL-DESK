/* Shared init + header wiring + per-page snapshot update functions for the
   Overview, Order Flow, and News pages. */

window.Main = {
  priceChart: null,
  volumeChart: null,

  init() {
    // Mode toggle (Simulated / Live)
    document.querySelectorAll(".mode-toggle .pill").forEach((btn) => {
      if (btn.disabled) return;
      btn.addEventListener("click", () => {
        fetch("/api/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ mode: btn.dataset.mode }),
        }).then(() => window.location.reload());
      });
    });

    // Feed-tier toggle (Overview page)
    document.querySelectorAll("[data-feed-tier]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tier = btn.dataset.feedTier;
        fetch("/api/config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ feed_tier: tier }),
        }).then((r) => r.json()).then((cfg) => {
          document.querySelectorAll("[data-feed-tier]").forEach((b) =>
            b.classList.toggle("active", b.dataset.feedTier === cfg.feed_tier)
          );
        });
      });
    });

    const page = document.body.dataset.page;
    if (page === "overview") this.priceChart = window.Charts.priceChart("price-chart");
    if (page === "orderflow") this.volumeChart = window.Charts.volumeChart("volume-chart");
  },

  updateHeader(s) {
    const tick = document.getElementById("tick-count");
    if (tick) tick.textContent = s.tick;
    const feedLabel = document.getElementById("feed-tier-label");
    if (feedLabel) feedLabel.textContent = s.feed_tier === "institutional" ? "FIX/WS" : "REST poll";
  },

  _setStat(id, value, tone) {
    const el = document.getElementById(id);
    if (!el) return;
    const v = el.querySelector(".value");
    v.textContent = value;
    v.className = `value tone-${tone || "neutral"}`;
  },

  updateOverview(s) {
    window.SessionClock.render("session-clock", s.session.active);
    this._setStat("stat-wti", `$${window.U.fmt2(s.price.wti)}`, s.price.wti_change >= 0 ? "bull" : "bear");
    this._setStat("stat-brent", `$${window.U.fmt2(s.price.brent)}`, s.price.brent_change >= 0 ? "bull" : "bear");
    this._setStat("stat-volz", window.U.fmt2(s.volume.z_score), s.volume.z_score >= s.config.z_threshold ? "amber" : "neutral");
    this._setStat("stat-loop", `${s.loop_score}/100`, s.loop_score > 60 ? "amber" : "neutral");

    // feed-tier stat pills
    const inst = s.feed_tier === "institutional";
    this._setStat("stat-latency", s.latency, inst ? "bull" : "amber");
    this._setStat("stat-cadence", inst ? "every tick" : "1 in 4 ticks", inst ? "bull" : "amber");
    this._setStat("stat-protocol", inst ? "FIX / WS" : "REST poll", "neutral");
    document.querySelectorAll("[data-feed-tier]").forEach((b) =>
      b.classList.toggle("active", b.dataset.feedTier === s.feed_tier)
    );

    window.Charts.updatePrice(this.priceChart, s.price.wti_history, s.price.brent_history);
    this._revealSkeletons("overview");
  },

  updateOrderflow(s) {
    window.OrderBook.render("orderbook", s.orderflow);
    window.Charts.updateVolume(this.volumeChart, s.volume.history, s.config.z_threshold);

    // volume panel badge: SIM in simulated mode, REAL in live mode
    const vbadge = document.getElementById("volume-badge");
    if (vbadge) {
      if (s.mode === "live") {
        vbadge.className = "badge-real";
        vbadge.textContent = "Real";
      } else {
        vbadge.className = "badge-sim";
        vbadge.textContent = "Sim";
      }
    }

    this._renderIcebergs(s.orderflow.icebergs);
    this._renderDarkPool(s.orderflow.dark_pool_prints);
    this._revealSkeletons("orderflow");
  },

  _renderIcebergs(list) {
    const el = document.getElementById("icebergs");
    if (!el) return;
    if (!list || !list.length) {
      el.innerHTML = `<div class="empty-state">No iceberg patterns detected yet.</div>`;
      return;
    }
    el.innerHTML = list
      .map(
        (ice) => `<div class="list-row mono">
          <span>$${window.U.fmt2(ice.price)}</span>
          <span class="tone-amber">${ice.clips} clips detected</span>
          <span class="muted">${window.U.timeOf(ice.time).hms}</span>
        </div>`
      )
      .join("");
  },

  _renderDarkPool(list) {
    const el = document.getElementById("darkpool");
    if (!el) return;
    if (!list || !list.length) {
      el.innerHTML = `<div class="empty-state">No block prints yet.</div>`;
      return;
    }
    el.innerHTML = list
      .map(
        (p) => `<div class="list-row mono">
          <span style="color:#2dd4bf">${window.U.esc(p.venue)}</span>
          <span>${p.size.toLocaleString()} lots @ $${p.price}</span>
          <span class="muted">${window.U.timeOf(p.time).hms}</span>
        </div>`
      )
      .join("");
  },

  updateNews(s) {
    const el = document.getElementById("news-feed");
    if (!el) return;
    const news = s.news || [];
    if (!news.length) {
      el.innerHTML = `<div class="empty-state">Waiting for the next wire hit…</div>`;
      return;
    }
    el.innerHTML = news
      .map((n) => {
        const t = window.U.timeOf(n.time);
        const score = Number(n.sentiment);
        const sc = score > 0.15 ? "bull" : score < -0.15 ? "bear" : "flat";
        const entities = (n.entities || [])
          .map((e) => `<span class="tag-entity">${window.U.esc(e)}</span>`)
          .join("");
        return `<div class="news-card">
          <div class="news-meta">
            <span class="news-source">${window.U.esc(n.source)}</span>
            <span class="mono">${t.hms}.${t.ms}</span>
          </div>
          <div class="news-headline">${window.U.esc(n.headline)}</div>
          <div class="news-tags">
            ${entities}
            <span class="tag-sent ${sc}">sentiment ${score > 0 ? "+" : ""}${window.U.fmt2(score)}</span>
            <span class="tag-conf">confidence ${window.U.pct(n.confidence)}%</span>
            ${n.market_moving ? '<span class="tag-mover">market-moving</span>' : ""}
          </div>
        </div>`;
      })
      .join("");
    this._revealSkeletons("news");
  },

  _revealSkeletons(page) {
    document.querySelectorAll(`[data-skeleton]`).forEach((sk) => sk.classList.add("hidden"));
    document.querySelectorAll(`[data-live-content]`).forEach((c) => c.classList.remove("hidden"));
  },
};

document.addEventListener("DOMContentLoaded", () => window.Main.init());
window.updateOverview = (s) => window.Main.updateOverview(s);
window.updateOrderflow = (s) => window.Main.updateOrderflow(s);
window.updateNews = (s) => window.Main.updateNews(s);
