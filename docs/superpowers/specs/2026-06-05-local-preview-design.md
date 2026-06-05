# Local Browser Preview for the TV Dashboard

**Date:** 2026-06-05
**Status:** Design — pending user review

## Goal

Let the user preview the TV dashboard in a browser by opening a single file from
the filesystem (drag into Chrome, double-click, `file://`), without running the
FastAPI server. The preview must reflect both layout/CSS changes and how real
data renders, so the user can iterate on the dashboard before committing and
deploying through git.

## Non-Goals

- Replacing local dev with `uvicorn` for backend work. The preview is purely
  frontend.
- Multiple data states / toggles. One realistic snapshot is enough.
- Live data from the Green or from `/api/dashboard`.
- Hot-reload. A manual browser refresh after a CSS/JS edit is fine.

## Approach

Add one new file: **`src/wall_dashboard/static/preview.html`**.

It lives alongside `dashboard.css` and `dashboard.js`, so relative paths
(`href="dashboard.css"`, `src="dashboard.js"`) work under `file://`. The user
opens it directly from the filesystem.

It duplicates `dashboard.html`'s `<main>` markup (~25 lines) and adds an inline
`<script>` block that:

1. Builds a realistic mock payload using the real `new Date()`.
2. Monkey-patches `window.fetch` so calls to `/api/dashboard` resolve with the
   mock payload instead of hitting the network.
3. Optionally (when `location.hash === "#tomorrow"`) shifts the global `Date`
   so `dashboard.js` thinks it is after the weather flip hour, exposing the
   TOMORROW view mode.

Then `dashboard.js` is loaded normally. Because the fetch override is installed
before the script runs, the dashboard renders exactly as it does in production,
just against canned data.

## File Layout

```
src/wall_dashboard/static/
  dashboard.css        (unchanged, reused via relative path)
  dashboard.js         (unchanged, reused via relative path)
  preview.html         (NEW — drag this into a browser)
```

`preview.html` ships inside the add-on Docker image as a side effect of being
under `static/`. That means it is also reachable on the Green at
`http://<green-ip>:8765/static/preview.html` — a nice bonus, costs nothing.

## Components

### 1. Static markup

A near-copy of `dashboard.html`'s `<main class="root">…</main>` block. The
`{{ now_iso }}` Jinja variable becomes a literal recent ISO string in
`data-now-iso` (its only consumer is `renderUpdated`, which falls back to
`Date.now()` if absent, so the exact value does not matter).

This is the one piece of duplication. If the dashboard's HTML structure
changes, `preview.html` must be updated too. CSS and JS are not duplicated.

### 2. Mock data generator

Inline `<script>` at the top of `<head>`, runs before `dashboard.js`:

```js
function buildMockData() {
  const now = new Date();
  const hours = [];
  // Generate 30 hourly entries from now forward, covering "today remaining"
  // and tomorrow up to ~9pm. dashboard.js filters this with its own window.
  for (let i = 0; i < 30; i++) {
    const d = new Date(now.getFullYear(), now.getMonth(), now.getDate(),
                       now.getHours() + i);
    const hourKey = `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}-${d.getHours()}`;
    hours.push({
      hourKey,
      hour: d.getHours(),
      temp: 68 + Math.round(8 * Math.sin(i / 4)),  // gentle wave
      precip: (i === 3 || i === 4) ? 30 : 0,        // two rainy hours
    });
  }
  const uvHours = hours.map((h, i) => ({
    hourKey: h.hourKey,
    value: i === 6 ? 7 : 5,                         // one "High" alert hour
    level: i === 6 ? "high" : "moderate",
  }));
  return {
    now_iso: now.toISOString(),
    weather: {
      available: true,
      current: { temp: 72, feels_like: 74, short: "Partly Sunny" },
      hours,
    },
    uv: { available: true, value: 5, category: "Moderate", level: "moderate",
          alert: false, hours: uvHours },
    aqi: { available: true, value: 42, category: "Good", level: "good",
           alert: false },
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
```

Values are illustrative — final tuning during implementation. Goal: at least
one hour shows the precip warning, at least one shows the UV warning, AQI and
UV badges both render in their non-alert tier.

### 3. Fetch interceptor

```js
const MOCK = buildMockData();
const realFetch = window.fetch;
window.fetch = (url, opts) => {
  if (typeof url === "string" && url.startsWith("/api/dashboard")) {
    return Promise.resolve(new Response(JSON.stringify(MOCK), {
      status: 200, headers: {"Content-Type": "application/json"},
    }));
  }
  return realFetch(url, opts);
};
```

Other fetches (none exist in `dashboard.js` today, but future-proofing) pass
through to the real `fetch`, which will simply fail under `file://` — acceptable.

### 4. `#tomorrow` view override (optional, opt-in)

When `location.hash === "#tomorrow"`, the script shifts the global `Date` so
that "now" appears to be 6pm today:

```js
if (location.hash === "#tomorrow") {
  const RealDate = Date;
  const fake = new RealDate();
  fake.setHours(18, 0, 0, 0);
  const offset = fake.getTime() - RealDate.now();
  const ShiftedDate = function (...args) {
    return args.length === 0
      ? new RealDate(RealDate.now() + offset)
      : new RealDate(...args);
  };
  ShiftedDate.now = () => RealDate.now() + offset;
  ShiftedDate.prototype = RealDate.prototype;
  // eslint-disable-next-line no-global-assign
  Date = ShiftedDate;
}
```

This makes `dashboard.js`'s `now.getHours() >= flipHour` evaluate true,
switching the hourly section into TOMORROW mode. `tickClock` will also display
6pm — visually obvious that the override is active.

Default (no hash): the preview shows whatever mode matches the real clock.

## Data Flow

```
preview.html opens in browser (file:// or http:// — both work)
  │
  ├─► inline <script>  (synchronous, runs first)
  │     ├─ optionally shifts Date
  │     ├─ builds MOCK payload from new Date()
  │     └─ overrides window.fetch for /api/dashboard
  │
  ├─► <link> loads dashboard.css           (relative path)
  │
  └─► <script defer> loads dashboard.js    (relative path)
        └─ refresh() calls fetch("/api/dashboard")
             └─ intercepted → returns MOCK
                  └─ renderWeather / renderHourly / renderAqi /
                     renderUv / renderTrains run normally
```

## Error Handling

The preview is a developer tool. Errors should be visible, not swallowed.

- **fetch fallthrough:** If `dashboard.js` ever adds a new endpoint, the
  passthrough call will fail under `file://` and log to console. That is the
  desired signal — the preview needs a new mock.
- **Date shift edge cases:** The `ShiftedDate` is only installed when the hash
  is exactly `#tomorrow`. Any other hash value is ignored. No exceptions
  thrown.
- **Stale markup:** If `dashboard.html` changes structure but `preview.html`
  does not, the preview will render against the old layout. No automated
  detection; relies on the user noticing during their normal review.

## Testing

This is a static developer tool with no automated tests. Verification is
manual:

1. Open `src/wall_dashboard/static/preview.html` in Chrome (`file://`).
2. Confirm: temperature, "Partly Sunny", AQI badge, UV badge, hourly grid
   (with one ☂ rain hour and one ☀ UV hour), train list.
3. Add `#tomorrow` to the URL, reload. Confirm: section label changes to
   "TOMORROW", clock shows 6:00 PM.

If `dashboard.js` ever gains a `tests/` peer to validate rendering against
fixtures, the same `MOCK` payload should be a reasonable starting fixture.
Out of scope for this design.

## Open Questions

None. Awaiting user review of this spec.

## Future Work (not in scope)

- A "force unavailable" toggle (e.g. `#no-trains`, `#no-weather`) to preview
  the unavailable states without editing the mock generator.
- Switchable mock states (happy / alert / empty) via dropdown.
- Generating the mock data from a fixture file committed under `tests/` so
  the same JSON powers both backend unit tests and the preview.
