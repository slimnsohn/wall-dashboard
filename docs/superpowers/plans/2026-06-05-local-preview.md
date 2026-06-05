# Local Browser Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `src/wall_dashboard/static/preview.html` so the TV dashboard renders under `file://` (drag-into-browser) without running the FastAPI server, by mocking `/api/dashboard` via a `window.fetch` override.

**Architecture:** One new static HTML file that sits next to the existing `dashboard.css` and `dashboard.js`. Inline `<script>` in `<head>` builds a realistic mock payload (anchored on the real `new Date()`), monkey-patches `window.fetch`, and optionally shifts the global `Date` when `location.hash === "#tomorrow"`. Then the unchanged `dashboard.js` runs and renders.

**Tech Stack:** Vanilla HTML/CSS/JS. No build step. No new dependencies. Loaded from the filesystem via `file://` or served from `/static/preview.html` by the existing FastAPI app.

**Spec:** `docs/superpowers/specs/2026-06-05-local-preview-design.md`

---

## File Structure

- **Create:** `src/wall_dashboard/static/preview.html` — the only new file.
- **Modify:** none.
- **Test:** verification is manual — see Task 5. No automated test file added.

The static dir already contains `dashboard.css` and `dashboard.js`. Putting `preview.html` here means relative `<link>` and `<script>` paths resolve correctly under both `file://` and `http://`.

---

## Task 1: Skeleton `preview.html` with duplicated markup

The first cut is the static HTML scaffold — a copy of `dashboard.html`'s body, references to the real CSS/JS, but no mock logic yet. This will render an empty dashboard (because `fetch("/api/dashboard")` fails under `file://`) — that's expected and we'll fix it in Task 2.

**Files:**
- Create: `src/wall_dashboard/static/preview.html`

- [ ] **Step 1: Create `preview.html` with markup copied from `dashboard.html`**

Write this exact content:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Wall Dashboard — Preview</title>
  <link rel="stylesheet" href="dashboard.css">
</head>
<body data-now-iso="2026-06-05T08:30:00-05:00">
  <main class="root">
    <header class="header">
      <div class="left">
        <div class="location-line">
          <span class="location">NORTHBROOK</span>
          <span class="now-temp" id="now-temp">--°</span>
        </div>
        <div class="weather-meta">
          <span class="short" id="weather-short"></span>
          <span class="feels" id="weather-feels"></span>
        </div>
        <div class="health-line">
          <span class="badge aqi-badge" id="aqi-badge">AQI --</span>
          <span class="badge uv-badge" id="uv-badge">UV --</span>
        </div>
      </div>
      <div class="right">
        <div class="date" id="date">—</div>
        <div class="time" id="time">--:--</div>
      </div>
    </header>

    <section class="section hourly-section" id="section-hourly">
      <div class="section-label"><span id="hourly-label">HOURLY</span></div>
      <div class="hourly" id="hourly"></div>
      <div class="section-unavailable" id="hourly-unavailable" hidden>weather unavailable</div>
    </section>

    <div class="flex-spacer"></div>

    <section class="section trains-section" id="section-trains">
      <div class="section-label">
        <span>NORTHBROOK TRAINS</span>
        <span class="updated" id="updated">—</span>
      </div>
      <ul class="train-list" id="trains"></ul>
      <div class="section-unavailable" id="trains-unavailable" hidden>trains unavailable</div>
    </section>
  </main>
  <script src="dashboard.js" defer></script>
</body>
</html>
```

This is a near-exact copy of `src/wall_dashboard/templates/dashboard.html` with two changes:
- `<title>` adds "— Preview"
- The Jinja `{{ now_iso }}` placeholder is replaced with a literal ISO string

- [ ] **Step 2: Open in browser, verify the skeleton loads CSS**

On Windows, double-click `src\wall_dashboard\static\preview.html` (or drag it into Chrome).

Expected:
- Browser tab title: "Wall Dashboard — Preview"
- Black background, the layout's frame, "NORTHBROOK", "--°", "AQI --", "UV --", "HOURLY" and "NORTHBROOK TRAINS" section labels all visible and styled per the real CSS.
- DevTools console shows ONE error from `dashboard.js`: `refresh TypeError: Failed to fetch` (or similar) — this is expected, because `/api/dashboard` does not resolve under `file://`. Task 2 fixes it.
- No error about missing `dashboard.css`.

If CSS looks unstyled: confirm `preview.html` is in `src/wall_dashboard/static/` next to `dashboard.css`, not somewhere else.

- [ ] **Step 3: Commit**

```bash
git add src/wall_dashboard/static/preview.html
GIT_AUTHOR_NAME='slimnsohn' GIT_AUTHOR_EMAIL='help.sohn@gmail.com' GIT_COMMITTER_NAME='slimnsohn' GIT_COMMITTER_EMAIL='help.sohn@gmail.com' git commit -m "feat(preview): scaffold static preview.html (no mock data yet)"
```

(The env-var prefix is because this repo's git identity is not configured globally on this machine. If `git config user.email` returns a value when you run it, you can drop the prefix.)

---

## Task 2: Mock-data generator + `fetch` override

Add the inline `<script>` in `<head>` that builds a realistic mock `/api/dashboard` payload and overrides `window.fetch` to return it. This must run **before** `dashboard.js` loads.

**Files:**
- Modify: `src/wall_dashboard/static/preview.html`

- [ ] **Step 1: Add the inline script to `<head>`**

Insert the following `<script>` block in `preview.html` immediately before the closing `</head>` tag (i.e., after the `<link rel="stylesheet">` line):

```html
  <script>
    // Build a realistic /api/dashboard payload anchored on real "now",
    // so the hourly window in dashboard.js (which uses new Date()) lines up.
    function buildMockData() {
      const now = new Date();
      const hours = [];
      for (let i = 0; i < 30; i++) {
        const d = new Date(now.getFullYear(), now.getMonth(), now.getDate(),
                           now.getHours() + i);
        const hourKey = `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}-${d.getHours()}`;
        hours.push({
          hourKey,
          hour: d.getHours(),
          temp: 68 + Math.round(8 * Math.sin(i / 4)),
          precip: (i === 3 || i === 4) ? 30 : 0,
        });
      }
      const uvHours = hours.map((h, i) => ({
        hourKey: h.hourKey,
        value: i === 6 ? 7 : 5,
        level: i === 6 ? "high" : "moderate",
      }));
      return {
        now_iso: now.toISOString(),
        weather: {
          available: true,
          current: { temp: 72, feels_like: 74, short: "Partly Sunny" },
          hours,
        },
        uv: {
          available: true, value: 5, category: "Moderate", level: "moderate",
          alert: false, hours: uvHours,
        },
        aqi: {
          available: true, value: 42, category: "Good", level: "good",
          alert: false,
        },
        metra: {
          available: true,
          arrivals: [
            { time: "8:42 AM", countdown_min: 12, countdown_str: "12 min" },
            { time: "9:14 AM", countdown_min: 44, countdown_str: "44 min" },
          ],
        },
        amtrak: {
          available: true,
          northbound: [
            { time: "9:30 AM", countdown_min: 60, countdown_str: "1 hr" },
          ],
          southbound: [],
        },
        weather_flip_hour: 17,
        weather_end_hour: 21,
      };
    }

    const __MOCK = buildMockData();
    const __realFetch = window.fetch;
    window.fetch = function (url, opts) {
      if (typeof url === "string" && url.startsWith("/api/dashboard")) {
        return Promise.resolve(new Response(JSON.stringify(__MOCK), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }));
      }
      return __realFetch ? __realFetch.call(window, url, opts)
                         : Promise.reject(new Error("fetch unavailable"));
    };
  </script>
```

Notes for the implementing engineer:
- The script is NOT `defer` — it must run synchronously before `dashboard.js` (which IS `defer`) so the override is in place when `refresh()` fires.
- `__MOCK` is captured once at page load. That's fine — the dashboard's `setInterval(refresh, REFRESH_MS)` will re-fetch every 30s, and each call returns the same canned payload. No memory leak: the same JSON is re-serialized cheaply on each call.
- `hourKey` format is `YYYY-M-D-H` with **un-padded** month/day/hour — this exactly matches how `dashboard.js` parses it (`parseHourKey` in `static/dashboard.js:76-81` uses `parseInt` and does not assume padding).

- [ ] **Step 2: Reload the browser and verify the dashboard fully renders**

Hard-reload `preview.html` (Ctrl+F5).

Expected (assuming you're opening this before 5pm local):
- Current temperature shows **72°**, "Partly Sunny" caption, "feels 74°".
- AQI badge: **AQI 42 · Good** (green tier).
- UV badge: **UV 5 · Moderate** (yellow/orange tier).
- Hourly grid: a row of hour cells starting at the current hour, each with a temp. At least one cell shows the ☂ rain icon with "30%". At least one cell shows the ☀ icon with "UV 7" (red tier).
- "Updated H:MM AM/PM" matches the current time.
- Train list: **two Metra rows** ("8:42 AM, 12 min" and "9:14 AM, 44 min") and **one Amtrak row** ("9:30 AM, 1 hr"), sorted by countdown — Metra 12 min first.
- DevTools console: clean, no errors.

If the hourly grid is empty: check that `now.getHours()` (in DevTools console) is between 0 and 21. If it's 22 or 23, the window `[now, 9pm]` is empty and the grid renders nothing — that's correct behavior of `dashboard.js`, not a bug in the preview. Reproduce mid-day.

If trains are missing: check DevTools console for a parse error in the `<script>` block.

- [ ] **Step 3: Commit**

```bash
git add src/wall_dashboard/static/preview.html
GIT_AUTHOR_NAME='slimnsohn' GIT_AUTHOR_EMAIL='help.sohn@gmail.com' GIT_COMMITTER_NAME='slimnsohn' GIT_COMMITTER_EMAIL='help.sohn@gmail.com' git commit -m "feat(preview): mock /api/dashboard via window.fetch override"
```

---

## Task 3: `#tomorrow` view-mode override

Add the opt-in `Date` shift so `preview.html#tomorrow` exposes the post-5pm TOMORROW view. Without this, you can only preview that mode by changing your system clock.

**Files:**
- Modify: `src/wall_dashboard/static/preview.html`

- [ ] **Step 1: Add the Date-shift block above `buildMockData`**

Inside the existing `<script>` in `<head>`, **before** the `function buildMockData()` declaration, insert:

```js
    // Opt-in: preview.html#tomorrow forces "now" to 6pm so dashboard.js
    // enters TOMORROW view-mode. The clock visibly shows 6:00 PM as a
    // signal that the override is active.
    if (location.hash === "#tomorrow") {
      const __RealDate = Date;
      const __fake = new __RealDate();
      __fake.setHours(18, 0, 0, 0);
      const __offset = __fake.getTime() - __RealDate.now();
      const __ShiftedDate = function (...args) {
        return args.length === 0
          ? new __RealDate(__RealDate.now() + __offset)
          : new __RealDate(...args);
      };
      __ShiftedDate.now = () => __RealDate.now() + __offset;
      __ShiftedDate.UTC = __RealDate.UTC;
      __ShiftedDate.parse = __RealDate.parse;
      __ShiftedDate.prototype = __RealDate.prototype;
      // eslint-disable-next-line no-global-assign
      Date = __ShiftedDate;
    }
```

This block must come before `buildMockData()` so the mock data is also generated against the shifted clock — guarantees the hourly grid has entries that fall inside the TOMORROW window (tomorrow 7am–9pm).

Why preserve `Date.UTC` / `Date.parse`: `dashboard.js` doesn't call them today, but they're cheap to keep and avoids a surprise if either is ever used.

- [ ] **Step 2: Verify the default (no hash) still works**

Hard-reload `preview.html` with NO hash. Confirm everything from Task 2 Step 2 still renders correctly. The section label should say **HOURLY** (before 5pm) and the clock should show real time.

- [ ] **Step 3: Verify `#tomorrow` flips the view**

In the address bar, append `#tomorrow` to the URL (e.g. `file:///C:/Users/slims/Desktop/repos/wall-dashboard/src/wall_dashboard/static/preview.html#tomorrow`) and reload.

Expected:
- Clock at top-right shows **6:00 PM** (or 6:00 PM-ish; it ticks every second).
- Section label changes from "HOURLY" to **"TOMORROW"**.
- Hourly grid: cells start at **7a** (tomorrow 7am) and extend toward 9p, each with a temp. The ☂ and ☀ alert cells will be in different positions than the default view — that's expected (the index-based mock pattern shifts with the data window).
- Everything else (badges, trains) renders unchanged.

If the clock doesn't change: the hash didn't take. Confirm the URL ends with literally `#tomorrow` (no trailing space).

If "TOMORROW" doesn't appear: open DevTools console, run `new Date().getHours()`. It must return `18`. If it returns the real hour, the script ordering is wrong — the Date shift must be above `buildMockData` AND in a non-`defer` script.

- [ ] **Step 4: Commit**

```bash
git add src/wall_dashboard/static/preview.html
GIT_AUTHOR_NAME='slimnsohn' GIT_AUTHOR_EMAIL='help.sohn@gmail.com' GIT_COMMITTER_NAME='slimnsohn' GIT_COMMITTER_EMAIL='help.sohn@gmail.com' git commit -m "feat(preview): #tomorrow hash forces post-5pm view mode"
```

---

## Task 4: Final pass — open in browser, eyeball every panel

This task has no code changes. It's a deliberate manual verification step before the plan is marked done.

**Files:** none.

- [ ] **Step 1: Default-mode visual audit**

Open `src/wall_dashboard/static/preview.html` in Chrome (drag the file in, or double-click). Walk through this checklist with eyes on the page:

- [ ] **Header — left side**
  - "NORTHBROOK" in the location color (per dashboard.css)
  - "72°" current temp
  - "Partly Sunny" short caption
  - "feels 74°" small text
  - "AQI 42 · Good" badge in the "good" tier color
  - "UV 5 · Moderate" badge in the "moderate" tier color
- [ ] **Header — right side**
  - Today's date in `Day Mon D` format
  - Current time in `H:MM AM/PM` format, updating every second
- [ ] **Hourly section**
  - Label says "HOURLY"
  - Row of hour cells, each with a label like `9a`, `10a`, `11a`, etc.
  - AM hours have one color, PM hours have a different (subtler) color per `dashboard.css`
  - At least one cell has the ☂ icon and a percentage (e.g. "30%")
  - At least one cell has the ☀ icon and "UV 7"
  - No cells wrap to a second row
- [ ] **Trains section**
  - Label says "NORTHBROOK TRAINS" with "Updated H:MM AM/PM" on the right (red color per the recent style change)
  - Three rows total, in countdown order:
    - "Metra 8:42 AM 12 min"
    - "Metra 9:14 AM 44 min"
    - "Amtrak 9:30 AM 1 hr"
  - No "trains unavailable" message
- [ ] **DevTools console: zero errors, zero warnings**

- [ ] **Step 2: `#tomorrow` mode visual audit**

Append `#tomorrow` to the URL, reload. Confirm:

- [ ] Clock shows "6:00 PM"
- [ ] Hourly label says "TOMORROW"
- [ ] Hourly cells start at "7a"
- [ ] All other panels (badges, trains) render identically to default mode

- [ ] **Step 3: Edit-reflect smoke test**

Open `src/wall_dashboard/static/dashboard.css` in your editor. Pick any visible style (e.g. `.location` color) and change it. Save. Hard-reload `preview.html` (Ctrl+F5). The change should appear immediately. Revert the CSS edit.

This proves the preview is reading the real CSS, not a stale copy — the main reason for committing this file in-tree.

- [ ] **Step 4: No commit needed.**

This task changes no files. If you discover a defect during the audit, fix it under the relevant earlier task and commit there; don't create a "fix it up" commit at the end.

---

## Self-Review

**1. Spec coverage:**
- Goal — covered (Task 1+2 deliver a working file:// preview)
- Approach (one file at `src/wall_dashboard/static/preview.html`, monkey-patch `window.fetch`, reuse real CSS/JS) — covered (Task 1, Task 2)
- Inline mock-data generator anchored on `new Date()` — covered (Task 2 Step 1)
- `#tomorrow` view-mode override — covered (Task 3)
- Manual verification (no automated tests) — covered (Task 4)
- Future work (state toggles, fixture extraction) — correctly excluded

**2. Placeholder scan:** no TBDs, no "add appropriate error handling", every code step has full code.

**3. Type/identifier consistency:** `__MOCK`, `__realFetch`, `__RealDate`, `__ShiftedDate`, `__offset`, `__fake`, `buildMockData` — used consistently across Tasks 2 and 3. `hourKey` format `YYYY-M-D-H` (unpadded) matches `dashboard.js:76-81`. Mock JSON shape matches every field consumed by `dashboard.js` (`renderWeather`, `renderHourly`, `renderBadge`, `renderTrains`, `renderUpdated`).
