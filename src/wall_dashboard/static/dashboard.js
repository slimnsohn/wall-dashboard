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

function renderHourly(w) {
  try {
    const host = document.getElementById("hourly");
    if (!host) return;
    if (!w || !w.available) {
      while (host.firstChild) host.removeChild(host.firstChild);
      setHidden("hourly-unavailable", false);
      return;
    }
    setHidden("hourly-unavailable", true);
    const hours = (w.hours || []).slice(0, MAX_HOURS);
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
      // Only show precip when there's actual chance of rain (skip 0% and null)
      if (h.precip != null && h.precip > 0) {
        const precip = document.createElement("div");
        precip.className = "p";
        precip.textContent = `${Math.round(h.precip)}%`;
        cell.appendChild(precip);
      }
      host.appendChild(cell);
    });
  } catch (e) {
    console.error("renderHourly", e);
  }
}

function renderAqi(a) {
  try {
    const line = document.getElementById("aqi-line");
    const text = document.getElementById("aqi-text");
    if (!line || !text) return;
    if (!a || !a.available) {
      text.textContent = "AQI unavailable";
      line.className = "aqi-line";
      return;
    }
    if (a.alert) {
      text.textContent = `⚠ AQI ${a.value} · ${a.category || ""}`.trim();
      line.className = "aqi-line alert " + (a.level || "");
    } else {
      text.textContent = `AQI ${a.value} · ${a.category || "Good"}`;
      line.className = "aqi-line good";
    }
  } catch (e) {
    console.error("renderAqi", e);
  }
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
    renderHourly(d.weather);
    renderAqi(d.aqi);
    renderTrains(d.metra, d.amtrak, d.now_iso);
    renderUpdated(d.now_iso);
  } catch (e) {
    console.error("refresh", e);
    // Transient failures keep last-good display on the TV
  }
}

/* ── OLED anti-burn-in: pixel nudge every hour ─────────── */

function pixelNudge() {
  const dx = Math.floor(Math.random() * 7) - 3;  // -3..3
  const dy = Math.floor(Math.random() * 7) - 3;
  document.body.style.transform = `translate(${dx}px, ${dy}px)`;
}

tickClock();
setInterval(tickClock, 1_000);
refresh();
setInterval(refresh, REFRESH_MS);
setInterval(pixelNudge, 3_600_000);  // every hour
