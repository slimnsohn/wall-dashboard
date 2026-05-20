"use strict";

const REFRESH_MS = 30_000;

function setText(id, v) {
  const el = document.getElementById(id);
  if (el && el.textContent !== v) el.textContent = v;
}

function render(data) {
  const host = document.getElementById("train-list");
  const empty = document.getElementById("empty");
  if (!host) return;
  while (host.firstChild) host.removeChild(host.firstChild);
  const trains = (data && data.trains) || [];
  empty.hidden = trains.length > 0;
  trains.forEach(t => {
    const li = document.createElement("li");
    const type = document.createElement("span");
    type.className = "t-type";
    type.textContent = t.type;
    const time = document.createElement("span");
    time.className = "t-time";
    time.textContent = t.time;
    const cd = document.createElement("span");
    cd.className = "t-countdown";
    cd.textContent = t.countdown_str;
    li.appendChild(type);
    li.appendChild(time);
    li.appendChild(cd);
    host.appendChild(li);
  });
  setText("updated", "Updated " + ((data && data.updated_at) || "-"));
}

async function refresh() {
  try {
    const r = await fetch("/api/trains", { cache: "no-store" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    render(await r.json());
  } catch (e) {
    console.error("trains refresh", e);
  }
}

refresh();
setInterval(refresh, REFRESH_MS);
