"use strict";

const REFRESH_MS = 30_000;

function tickClock() {
  const now = new Date();
  const h = ((now.getHours() + 11) % 12) + 1;
  const m = String(now.getMinutes()).padStart(2, "0");
  const ampm = now.getHours() < 12 ? "AM" : "PM";
  setText("clock", `${h}:${m} ${ampm}`);
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el && el.textContent !== value) el.textContent = value;
}

function setUnavailable(panelId, isUnavailable) {
  const panel = document.getElementById(panelId);
  if (!panel) return;
  const overlay = panel.querySelector(".unavailable");
  if (overlay) overlay.hidden = !isUnavailable;
}

function formatHourLabel(h) {
  const period = h < 12 ? "a" : "p";
  const h12 = h % 12 || 12;
  return `${h12}${period}`;
}

function renderWeather(w) {
  try {
    if (!w || !w.available) { setUnavailable("panel-weather", true); return; }
    setUnavailable("panel-weather", false);
    const cur = w.current || {};
    setText("weather-temp", cur.temp != null ? `${Math.round(cur.temp)}°` : "--");
    const showFeels = cur.temp != null && cur.feels_like != null && cur.feels_like !== cur.temp;
    setText("weather-feels", showFeels ? `feels ${Math.round(cur.feels_like)}°` : "");
    setText("weather-short", cur.short || "");
    const host = document.getElementById("weather-hours");
    if (!host) return;
    const hours = (w.hours || []).slice(0, 8);
    while (host.firstChild) host.removeChild(host.firstChild);
    hours.forEach(h => {
      const cell = document.createElement("div");
      cell.className = "hour";
      const label = document.createElement("div");
      label.className = "hour-label";
      label.textContent = formatHourLabel(h.hour);
      const temp = document.createElement("div");
      temp.className = "hour-temp";
      temp.textContent = h.temp != null ? `${Math.round(h.temp)}°` : "--";
      cell.appendChild(label);
      cell.appendChild(temp);
      host.appendChild(cell);
    });
  } catch (e) {
    console.error("renderWeather", e);
    setUnavailable("panel-weather", true);
  }
}

function renderAqi(a) {
  try {
    if (!a || !a.available) { setUnavailable("panel-aqi", true); return; }
    setUnavailable("panel-aqi", false);
    const el = document.getElementById("aqi-value");
    if (el) {
      el.textContent = String(a.value);
      el.className = "aqi-value " + (a.level || "");
    }
    setText("aqi-category", a.category || "");
  } catch (e) {
    console.error("renderAqi", e);
    setUnavailable("panel-aqi", true);
  }
}

function renderTrainList(listId, items) {
  const host = document.getElementById(listId);
  if (!host) return;
  while (host.firstChild) host.removeChild(host.firstChild);
  items.slice(0, 4).forEach(it => {
    const li = document.createElement("li");
    const route = document.createElement("span");
    route.className = "train-route";
    route.textContent = it.route || it.type || "";
    const time = document.createElement("span");
    time.className = "train-time";
    time.textContent = it.time;
    const cd = document.createElement("span");
    cd.className = "train-countdown" + (it.delayed ? " delayed" : "");
    cd.textContent = it.countdown_str || "";
    li.appendChild(route);
    li.appendChild(time);
    li.appendChild(cd);
    host.appendChild(li);
  });
}

function renderMetra(m) {
  try {
    if (!m || !m.available) { setUnavailable("panel-metra", true); return; }
    setUnavailable("panel-metra", false);
    const items = (m.arrivals || []).map(a => ({
      route: a.route_id,
      time: a.time,
      countdown_str: a.countdown_str,
      delayed: false,
    }));
    renderTrainList("metra-list", items);
  } catch (e) {
    console.error("renderMetra", e);
    setUnavailable("panel-metra", true);
  }
}

function renderAmtrak(a) {
  try {
    if (!a || !a.available) { setUnavailable("panel-amtrak", true); return; }
    setUnavailable("panel-amtrak", false);
    const all = [].concat(a.northbound || [], a.southbound || []);
    const items = all.map(t => ({
      route: `Amtrak ${t.direction || ""} ${t.trainNum || ""}`.trim(),
      time: t.time,
      countdown_str: t.countdown_str,
    }));
    items.sort((x, y) => (x.countdown_min || 0) - (y.countdown_min || 0));
    renderTrainList("amtrak-list", items);
  } catch (e) {
    console.error("renderAmtrak", e);
    setUnavailable("panel-amtrak", true);
  }
}

async function refresh() {
  try {
    const r = await fetch("/api/dashboard", { cache: "no-store" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    renderWeather(data.weather);
    renderAqi(data.aqi);
    renderMetra(data.metra);
    renderAmtrak(data.amtrak);
  } catch (e) {
    console.error("refresh", e);
    // Don't blank panels on transient fetch failure - last-good state stays
  }
}

tickClock();
setInterval(tickClock, 1_000);
refresh();
setInterval(refresh, REFRESH_MS);
