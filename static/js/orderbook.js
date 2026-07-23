/* Renders the simulated bid/ask ladder. Ported from the JSX OrderBookLadder. */

window.OrderBook = {
  render(containerId, orderflow) {
    const el = document.getElementById(containerId);
    if (!el) return;
    const bids = orderflow.bids || [];
    const asks = orderflow.asks || [];
    const imb = orderflow.imbalance || 0;
    const maxSize = Math.max(1, ...bids.map((b) => b.size), ...asks.map((a) => a.size));

    const bidRows = bids
      .map(
        (b) => `
      <div class="row">
        <div class="bar bid" style="width:${(b.size / maxSize) * 100}%"></div>
        <div class="content bid-text"><span>${b.size}</span><span>${b.price}</span></div>
      </div>`
      )
      .join("");

    const askRows = asks
      .map(
        (a) => `
      <div class="row">
        <div class="bar ask" style="width:${(a.size / maxSize) * 100}%"></div>
        <div class="content ask-text"><span>${a.price}</span><span>${a.size}</span></div>
      </div>`
      )
      .join("");

    const imbClass = imb > 0 ? "tone-bull" : "tone-bear";
    el.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <span class="small muted">Depth of book (simulated Level 2)</span>
        <span class="mono ${imbClass}" style="font-weight:600">imbalance ${imb > 0 ? "+" : ""}${window.U.fmt2(imb)}</span>
      </div>
      <div class="ladder">
        <div><div class="col-label">BID</div>${bidRows}</div>
        <div><div class="col-label">ASK</div>${askRows}</div>
      </div>`;
  },
};
