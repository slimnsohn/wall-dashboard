# Wall Dashboard

Glanceable wall-mounted TV dashboard (Metra + Amtrak + weather + AQI for Northbrook)
plus a phone trains view and an iOS Scriptable widget. Python/FastAPI service
running as a native Home Assistant add-on on the HA Green (HAOS, ARM64).

## Layout
- `src/wall_dashboard/` — Python service (FastAPI + APScheduler)
- `src/wall_dashboard/templates/`, `static/` — vanilla HTML/CSS/JS for TV + phone views
- `scriptable/northbrook-trains.js` — iOS widget (Scriptable app)
- `tests/` — pytest, including a panel-isolation regression test

## Rules
- API keys (Metra token) live in `.env` on the Green, never in code or in git.
- Each data-source module returns `{available, error, ...}` and never raises.
  Source failures show as "data unavailable" in their panel only.
- No pandas, no numpy, no heavy native deps (ARM64 + small image).
- Chat-widget exception: TV is a non-interactive kiosk display.

## Deploy
See `README.md`. Native HA add-on at `/addons/wall-dashboard/` on the Green.
SSH `git pull` + HA UI "Rebuild" to update.
