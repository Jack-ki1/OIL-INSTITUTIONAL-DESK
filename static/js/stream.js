/* Opens the EventSource connection and fans each snapshot out to the update
   functions relevant to the currently visible page (via body[data-page]).
   Shows a "reconnecting…" indicator on error, cleared on the next message. */

(function () {
  const page = document.body.dataset.page;
  const reconnectEl = document.getElementById("reconnecting");

  const handlers = {
    overview: () => window.updateOverview,
    orderflow: () => window.updateOrderflow,
    news: () => window.updateNews,
    alerts: () => window.updateAlerts,
  };

  const source = new EventSource("/stream");

  source.onmessage = (event) => {
    if (reconnectEl) reconnectEl.classList.add("hidden");
    let snapshot;
    try {
      snapshot = JSON.parse(event.data);
    } catch (e) {
      return;
    }
    if (window.Main && window.Main.updateHeader) window.Main.updateHeader(snapshot);
    const getHandler = handlers[page];
    const fn = getHandler ? getHandler() : null;
    if (typeof fn === "function") fn(snapshot);
  };

  source.onerror = () => {
    // EventSource auto-reconnects; just surface the state honestly.
    if (reconnectEl) reconnectEl.classList.remove("hidden");
  };
})();
