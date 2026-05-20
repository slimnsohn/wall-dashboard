"use strict";

const REFRESH_MS = 30_000;
const MAX_TRAINS = 3;
const MAX_HOURS = 10;

const DAY_NAMES = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function setText(id, value) {
  const el = document.getElementById(id);
  if (el && el.textContent !== value) el.textContent = value;
}

function setHidden(id, hidden) {
  const el = document.getElementById(id);
  if (el) el.hidden = hidden;
}

function formatHourLabel(h) {
  const period = h < 12 ? "a" : "p";
  const h12 = h % 12 || 12;
  return `${h12}${period}`;
}

function tickClock() {
  const now = new Date();
  const day = DAY_NAMES[now.getDay()];
  const month = MONTH_NAMES[now.getMonth()];
  setText("date", `${day} ${month} ${now.getDate()}`);
  const h = ((now.getHours() + 11) % 12) + 1;
  const m = String(now.getMinutes()).padStart(2, "0");
  const ampm = now.getHours() < 12 ? "AM" : "PM";
  setText("time", `${h}:${m} ${ampm}`);
}

/* ── Renderers ──────────────────────────────────────────── */

function renderWeather(w) {
  try {
    if (!w || !w.available) {
      setText("now-temp", "--°");
      setText("weather-short", "");
      setText("weather-feels", "");
      // Hourly grid handled in renderHourly
      return;
    }
    const cur = w.current || {};
    setText("now-temp", cur.temp != null ? `${Math.round(cur.temp)}°` : "--°");
    setText("weather-short", cur.short || "");
    const showFeels = cur.temp != null && cur.feels_like != null
      && Math.round(cur.feels_like) !== Math.round(cur.temp);
    setText("weather-feels", showFeels ? `feels ${Math.round(cur.feels_like)}°` : "");
  } catch (e) {
    console.error("renderWeather", e);
  }
}

// Per-hour warning: rain wins over UV (rain matters more for "what to bring").
// Both have visibility thresholds so the layout stays clean during mild hours.
const PRECIP_THRESHOLD_PCT = 20;
const UV_THRESHOLD = 4;  // EPA upper "Moderate" (4-5) and above

function hourlyWarning(h, uvEntry) {
  if (h.precip != null && h.precip >= PRECIP_THRESHOLD_PCT) {
    return { kind: "precip", icon: "☂", value: `${Math.round(h.precip)}%` };
  }
  if (uvEntry && uvEntry.value >= UV_THRESHOLD) {
    return { kind: "uv", icon: "☀", value: `UV ${uvEntry.value}`, level: uvEntry.level };
  }
  return null;
}

// "YYYY-MM-DD-H" (H is not zero-padded) -> Date at the start of that hour.
function parseHourKey(key) {
  const parts = (key || "").split("-");
  if (parts.length !== 4) return null;
  return new Date(parseInt(parts[0]), parseInt(parts[1]) - 1,
                  parseInt(parts[2]), parseInt(parts[3]));
}

function renderHourly(w, uvData) {
  try {
    const host = document.getElementById("hourly");
    if (!host) return;
    if (!w || !w.available) {
      while (host.firstChild) host.removeChild(host.firstChild);
      setHidden("hourly-unavailable", false);
      return;
    }
    setHidden("hourly-unavailable", true);
    // Drop hours whose hour-start has already passed — the current hour stays
    // visible until the next clock hour begins, then it rolls off and a new
    // hour appears at the tail. The 30s refresh loop picks up the change.
    const now = new Date();
    const currentHourStart = new Date(
      now.getFullYear(), now.getMonth(), now.getDate(), now.getHours()
    ).getTime();
    const hours = (w.hours || [])
      .filter(h => {
        const d = parseHourKey(h.hourKey);
        return d && d.getTime() >= currentHourStart;
      })
      .slice(0, MAX_HOURS);

    // Build hourKey -> UV record lookup
    const uvByKey = {};
    if (uvData && uvData.available && Array.isArray(uvData.hours)) {
      uvData.hours.forEach(u => { uvByKey[u.hourKey] = u; });
    }

    while (host.firstChild) host.removeChild(host.firstChild);
    hours.forEach(h => {
      const cell = document.createElement("div");
      cell.className = "hour";
      const label = document.createElement("div");
      label.className = "h " + (h.hour < 12 ? "am" : "pm");
      label.textContent = formatHourLabel(h.hour);
      const temp = document.createElement("div");
      temp.className = "t";
      temp.textContent = h.temp != null ? `${Math.round(h.temp)}°` : "--";
      cell.appendChild(label);
      cell.appendChild(temp);

      const warn = hourlyWarning(h, uvByKey[h.hourKey]);
      if (warn) {
        const colorClass = warn.kind === "precip" ? "precip" : (warn.level || "");
        const icon = document.createElement("div");
        icon.className = `wicon ${colorClass}`;
        icon.textContent = warn.icon;
        const value = document.createElement("div");
        value.className = `wval ${colorClass}`;
        value.textContent = warn.value;
        cell.appendChild(icon);
        cell.appendChild(value);
      }

      host.appendChild(cell);
    });
  } catch (e) {
    console.error("renderHourly", e);
  }
}

function renderBadge(elId, kind, data) {
  // kind: "AQI" or "UV". data: {available, value, category, level, alert}
  const el = document.getElementById(elId);
  if (!el) return;
  if (!data || !data.available) {
    el.textContent = `${kind} —`;
    el.className = `badge ${elId}`;
    return;
  }
  if (data.alert) {
    el.textContent = `⚠ ${kind} ${data.value} · ${data.category || ""}`.trim();
    el.className = `badge ${elId} alert ${data.level || ""}`;
  } else {
    const cat = data.category || (kind === "AQI" ? "Good" : "Low");
    el.textContent = `${kind} ${data.value} · ${cat}`;
    el.className = `badge ${elId} ${data.level || "good"}`;
  }
}

function renderAqi(a) {
  try { renderBadge("aqi-badge", "AQI", a); }
  catch (e) { console.error("renderAqi", e); }
}

function renderUv(u) {
  try { renderBadge("uv-badge", "UV", u); }
  catch (e) { console.error("renderUv", e); }
}

function mergeTrains(metra, amtrak, now) {
  const items = [];
  if (metra && metra.available) {
    (metra.arrivals || []).forEach(a => {
      items.push({
        type: "Metra",
        time: a.time,
        countdown_min: a.countdown_min,
        countdown_str: a.countdown_str,
      });
    });
  }
  if (amtrak && amtrak.available) {
    ["northbound", "southbound"].forEach(group => {
      (amtrak[group] || []).forEach(t => {
        items.push({
          type: "Amtrak",
          time: t.time,
          countdown_min: t.countdown_min,
          countdown_str: t.countdown_str,
        });
      });
    });
  }
  items.sort((a, b) => (a.countdown_min || 0) - (b.countdown_min || 0));
  return items.slice(0, MAX_TRAINS);
}

function renderTrains(metra, amtrak, nowIso) {
  try {
    const host = document.getElementById("trains");
    if (!host) return;
    const metraOk = metra && metra.available;
    const amtrakOk = amtrak && amtrak.available;
    if (!metraOk && !amtrakOk) {
      while (host.firstChild) host.removeChild(host.firstChild);
      setHidden("trains-unavailable", false);
      return;
    }
    setHidden("trains-unavailable", true);
    const trains = mergeTrains(metra, amtrak, new Date(nowIso || Date.now()));
    while (host.firstChild) host.removeChild(host.firstChild);
    trains.forEach(t => {
      const li = document.createElement("li");
      const type = document.createElement("span"); type.className = "type"; type.textContent = t.type;
      const time = document.createElement("span"); time.className = "time"; time.textContent = t.time;
      const cd = document.createElement("span"); cd.className = "cd"; cd.textContent = t.countdown_str;
      li.appendChild(type);
      li.appendChild(time);
      li.appendChild(cd);
      host.appendChild(li);
    });
  } catch (e) {
    console.error("renderTrains", e);
  }
}

function renderUpdated(nowIso) {
  try {
    const dt = nowIso ? new Date(nowIso) : new Date();
    const h = ((dt.getHours() + 11) % 12) + 1;
    const m = String(dt.getMinutes()).padStart(2, "0");
    const ampm = dt.getHours() < 12 ? "AM" : "PM";
    setText("updated", `Updated ${h}:${m} ${ampm}`);
  } catch (e) {
    console.error("renderUpdated", e);
  }
}

/* ── Refresh loop ───────────────────────────────────────── */

async function refresh() {
  try {
    const r = await fetch("/api/dashboard", { cache: "no-store" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    renderWeather(d.weather);
    renderHourly(d.weather, d.uv);
    renderAqi(d.aqi);
    renderUv(d.uv);
    renderTrains(d.metra, d.amtrak, d.now_iso);
    renderUpdated(d.now_iso);
  } catch (e) {
    console.error("refresh", e);
    // Transient failures keep last-good display on the TV
  }
}

/* ── OLED anti-burn-in: pixel nudge every 5 minutes ────── */

const NUDGE_MS = 300_000;       // 5 minutes
const NUDGE_RANGE = 8;          // pixels: -8..+8 in each axis

function pixelNudge() {
  const dx = Math.floor(Math.random() * (NUDGE_RANGE * 2 + 1)) - NUDGE_RANGE;
  const dy = Math.floor(Math.random() * (NUDGE_RANGE * 2 + 1)) - NUDGE_RANGE;
  document.body.style.transform = `translate(${dx}px, ${dy}px)`;
}

tickClock();
setInterval(tickClock, 1_000);
refresh();
setInterval(refresh, REFRESH_MS);
pixelNudge();
setInterval(pixelNudge, NUDGE_MS);
