# Editing the Wall Dashboard

Quick-start for making visual/layout/data-rendering tweaks. Assumes the add-on is
already deployed to the Green. For first-time setup see `README.md`.

## What this is (1 paragraph)

Northbrook TV dashboard. One FastAPI process serves a vanilla HTML/CSS/JS frontend
that polls `/api/dashboard` every 30s. Runs as an HA add-on on the HA Green;
Fire Stick displays it. Most edits never touch Python — they're CSS, HTML, or
JS in `src/wall_dashboard/static/` and `src/wall_dashboard/templates/`.

## The edit loop

1. Edit a file (see table below).
2. Open `src/wall_dashboard/static/preview.html` in Chrome (drag-and-drop or
   double-click — works from `file://`).
3. Refresh after each save.
4. To see the post-5pm "TOMORROW" view, add `#tomorrow` to the URL.
5. When it looks right, commit, `git push`, then deploy.

No backend server needed for the preview — it mocks `/api/dashboard` in the
browser via a `window.fetch` override (see the `<script>` block at the top of
`preview.html`).

## Where to edit what

| Want to change… | Edit… |
|---|---|
| Colors, fonts, spacing, sizes | `src/wall_dashboard/static/dashboard.css` |
| What's shown / element order | `src/wall_dashboard/templates/dashboard.html` **AND** `src/wall_dashboard/static/preview.html` (keep their `<main>` blocks in sync) |
| How data renders (formatting, thresholds, max items) | `src/wall_dashboard/static/dashboard.js` |
| Mock data the preview uses | `src/wall_dashboard/static/preview.html` (the `buildMockData` function) |
| What data is fetched from the internet | `src/wall_dashboard/{weather,metra,amtrak,aqi,uv}.py` (Python — heavier change) |
| Times the "TOMORROW" mode flips on | `weather_flip_hour` / `weather_end_hour` in settings (defaults: 17 / 21) |

### The drift gotcha

`preview.html` duplicates the `<main>` markup from `dashboard.html`. If you add,
remove, or rename an element in one, do it in the other too. CSS and JS are
shared — only the body markup is duplicated.

## Deploy (after committing)

```bash
# On this Windows box:
git push

# SSH to the Green:
ssh root@<green-ip>
cd /addons/wall-dashboard && git pull

# Then in HA UI: Settings → Add-ons → Wall Dashboard → "Rebuild"
# Fire Stick auto-refreshes every 30s.
```

CSS/JS/HTML-only changes still need a Rebuild — the add-on is a Docker image
that bakes the static files in.

## Data shape (what the frontend renders)

`/api/dashboard` returns:

```
{
  now_iso,                  // ISO timestamp, used for "Updated 8:42 AM"
  weather_flip_hour,        // hour (0-23) when hourly section switches to TOMORROW
  weather_end_hour,         // last hour shown in the hourly grid
  weather: {
    available, error?,
    current: { temp, feels_like, short },
    hours: [{ hourKey, hour, temp, precip }]   // hourKey = "YYYY-M-D-H" (unpadded)
  },
  uv: {
    available, value, category, level, alert,
    hours: [{ hourKey, value, level }]         // joins to weather.hours by hourKey
  },
  aqi:    { available, value, category, level, alert },
  metra:  { available, arrivals: [{ time, countdown_min, countdown_str }] },
  amtrak: { available, northbound: [...], southbound: [...] },  // same arrival shape
  astro:  { available, sunsets_iso: [today_iso, tomorrow_iso] } // gates UV display past sunset
}
```

Every data source returns `{available: false, error: ...}` if it fails — its
panel shows "data unavailable" but the rest of the screen keeps working. **Never
let a data source raise.**

## What NOT to touch unless you mean to

- **`.env` on the Green** — holds `METRA_TOKEN`. Never in code, never in git.
- **`src/wall_dashboard/{weather,metra,amtrak,aqi,uv}.py`** — only if changing
  what data is fetched. Frontend tweaks don't need these.
- **`tests/`** — keep `pytest -v` green. Especially the panel-isolation test
  (one source failing must not break others).
- **Dependencies** — no pandas, no numpy, no heavy native deps. The image runs
  on the Green's ARM64 and stays small.

## Quick file map

```
src/wall_dashboard/
  static/
    dashboard.css   ← colors, layout, sizes  (most visual tweaks land here)
    dashboard.js    ← rendering logic, refresh loop, OLED nudge
    preview.html    ← drag into Chrome to preview; contains mock data
  templates/
    dashboard.html  ← TV page structure (keep in sync with preview.html)
    trains.html     ← phone-only trains view
  web.py            ← FastAPI routes and /api/dashboard aggregator
  {weather,metra,amtrak,aqi,uv}.py   ← data sources
```

## Constraints (from CLAUDE.md)

- Source failures stay scoped to their panel.
- No pandas/numpy/heavy native deps (ARM64 + small image).
- API keys live in `.env` on the Green, never in code or git.
- TV is a non-interactive kiosk display (no click handlers needed).
