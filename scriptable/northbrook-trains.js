// Northbrook Trains - Scriptable iOS home-screen widget.
//
// Setup:
//   1. Install the free "Scriptable" app from the App Store.
//   2. Scriptable -> + -> paste this whole file -> name it "Northbrook Trains".
//   3. Set BASE_URL below to your HA Green's LAN URL (e.g. http://192.168.1.50:8765).
//   4. Long-press the home screen -> add a "Scriptable" widget -> choose this script.
//
// Reads the wall-dashboard JSON route (/api/trains):
//   { location, trains: [{ type, time, countdown_min, countdown_str }], updated_at }
//
// Note: the wall-dashboard service is LAN-only by default - this widget will
// only refresh when the phone is on home wifi. To add cellular reach, expose
// the service via Nabu Casa, Cloudflare Tunnel, or Tailscale.

const BASE_URL = "PASTE_YOUR_GREEN_LAN_URL_HERE";  // e.g. "http://192.168.1.50:8765"

const COLORS = {
  bg: new Color("#0a0a0a"),
  title: new Color("#9a9a9a"),
  primary: new Color("#e0e0e0"),
  accent: new Color("#7ab8ff"),
  countdown: new Color("#9a9a9a"),
  muted: new Color("#6a6a6a"),
};

async function fetchTrains() {
  const req = new Request(BASE_URL + "/api/trains");
  req.timeoutInterval = 15;
  return await req.loadJSON();
}

function header(widget, locationName) {
  const t = widget.addText((locationName || "Northbrook").toUpperCase());
  t.font = Font.semiboldSystemFont(12);
  t.textColor = COLORS.title;
}

function trainRow(widget, train) {
  const row = widget.addStack();
  row.centerAlignContent();
  const type = row.addText(train.type + "  ");
  type.font = Font.mediumSystemFont(16);
  type.textColor = COLORS.accent;
  const time = row.addText(train.time || "");
  time.font = Font.mediumSystemFont(16);
  time.textColor = COLORS.primary;
  row.addSpacer();
  const cd = row.addText(train.countdown_str || "");
  cd.font = Font.systemFont(14);
  cd.textColor = COLORS.countdown;
}

function buildWidget(data) {
  const w = new ListWidget();
  w.backgroundColor = COLORS.bg;
  w.setPadding(14, 16, 14, 16);
  header(w, data && data.location);
  w.addSpacer(9);
  const trains = (data && data.trains) || [];
  if (trains.length === 0) {
    const empty = w.addText("No upcoming trains");
    empty.font = Font.systemFont(15);
    empty.textColor = COLORS.muted;
  } else {
    const limit = config.widgetFamily === "small" ? 2 : 3;
    trains.slice(0, limit).forEach(function (train, i) {
      if (i > 0) w.addSpacer(8);
      trainRow(w, train);
    });
  }
  w.addSpacer();
  const upd = w.addText("Updated " + ((data && data.updated_at) || "-"));
  upd.font = Font.systemFont(10);
  upd.textColor = COLORS.muted;
  return w;
}

function messageWidget(message) {
  const w = new ListWidget();
  w.backgroundColor = COLORS.bg;
  w.setPadding(14, 16, 14, 16);
  header(w, "Northbrook");
  w.addSpacer(9);
  const m = w.addText(message);
  m.font = Font.systemFont(14);
  m.textColor = COLORS.muted;
  return w;
}

let widget;
try {
  if (BASE_URL.indexOf("PASTE_") === 0) {
    widget = messageWidget("Set BASE_URL in the script");
  } else {
    widget = buildWidget(await fetchTrains());
  }
} catch (e) {
  widget = messageWidget("Couldn't load trains");
}

if (config.runsInWidget) {
  Script.setWidget(widget);
} else {
  widget.presentMedium();
}
Script.complete();
