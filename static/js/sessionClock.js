/* Draws the 24h SVG session clock. Geometry ported from the JSX SessionClock:
   each hour maps to (h/24)*360 - 90 degrees; sessions are drawn as arcs. */

window.SessionClock = {
  SESSIONS: [
    { key: "asian", label: "Asian", start: 0, end: 8, color: "#38bdf8" },
    { key: "london", label: "London", start: 8, end: 13, color: "#34d399" },
    { key: "ny", label: "New York", start: 13, end: 21, color: "#fbbf24" },
    { key: "off", label: "Off-hours", start: 21, end: 24, color: "#64748b" },
  ],

  sessionForHour(h) {
    return this.SESSIONS.find((s) => h >= s.start && h < s.end) || this.SESSIONS[3];
  },

  _angle(h) {
    return ((h / 24) * 360 - 90) * (Math.PI / 180);
  },

  _arc(start, end, color, cx, cy, r) {
    const a1 = this._angle(start);
    const a2 = this._angle(end);
    const x1 = cx + r * Math.cos(a1);
    const y1 = cy + r * Math.sin(a1);
    const x2 = cx + r * Math.cos(a2);
    const y2 = cy + r * Math.sin(a2);
    const large = end - start > 12 ? 1 : 0;
    return `<path d="M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}" stroke="${color}" stroke-width="9" fill="none" stroke-linecap="round" opacity="0.85" />`;
  },

  render(containerId, activeKey) {
    const el = document.getElementById(containerId);
    if (!el) return;
    const cx = 60, cy = 60, r = 46;
    const now = new Date();
    const hourFloat = now.getUTCHours() + now.getUTCMinutes() / 60;
    const ha = this._angle(hourFloat);
    const hx = cx + (r - 6) * Math.cos(ha);
    const hy = cy + (r - 6) * Math.sin(ha);
    const current = activeKey
      ? this.SESSIONS.find((s) => s.key === activeKey) || this.sessionForHour(now.getUTCHours())
      : this.sessionForHour(now.getUTCHours());

    const arcs = this.SESSIONS.filter((s) => s.key !== "off")
      .map((s) => this._arc(s.start, s.end, s.color, cx, cy, r))
      .join("");

    const legend = this.SESSIONS.filter((s) => s.key !== "off")
      .map((s) => `<span><span class="dot" style="background:${s.color}"></span>${s.label}</span>`)
      .join("");

    const utc = now.toUTCString().slice(17, 25);

    el.innerHTML = `
      <div class="session-clock">
        <svg width="120" height="120" viewBox="0 0 120 120">
          <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#1e293b" stroke-width="9" />
          ${arcs}
          <line x1="${cx}" y1="${cy}" x2="${hx}" y2="${hy}" stroke="#f8fafc" stroke-width="2" />
          <circle cx="${cx}" cy="${cy}" r="3" fill="#f8fafc" />
        </svg>
        <div>
          <div class="tiny muted" style="text-transform:uppercase;letter-spacing:0.15em">Active session (UTC)</div>
          <div style="font-size:20px;font-weight:600;color:${current.color}">${current.label}</div>
          <div class="mono tiny muted">${utc} UTC</div>
          <div class="session-legend">${legend}</div>
        </div>
      </div>`;
  },
};
