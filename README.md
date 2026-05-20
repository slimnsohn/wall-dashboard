# Wall Dashboard

A wall-mounted TV dashboard - Northbrook trains (Metra MD-N + Amtrak), Glenview-area
weather, and current US AQI - plus a phone trains view and an iOS Scriptable widget.
Runs as a native Home Assistant add-on on a Home Assistant Green (HAOS, ARM64).

## Architecture

One Python process. One FastAPI app (port 8765). One Docker container. Deployed
as an HA Local Add-on. APScheduler runs the weekly Amtrak GTFS refresh inside
the same process.

## Local development (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env                   # fill in METRA_TOKEN etc.
pytest -v
uvicorn wall_dashboard.web:app --reload --port 8765
```

Then visit `http://localhost:8765/`.

CLI for manual probing:

```powershell
wall-dashboard probe              # hits every data source, shows availability
wall-dashboard stations Glenview  # resolve a stop_id (errors if ambiguous)
wall-dashboard bootstrap-nws      # prints the NWS_FORECAST_HOURLY_URL to paste into .env
wall-dashboard refresh-amtrak     # force an immediate weekly Amtrak refresh
```

## Deploy to Home Assistant Green (HAOS)

One-time setup on the Green:

1. **Install the Advanced SSH & Web Terminal add-on.** HA Settings -> Add-ons -> Add-on Store. It's in the default catalog - no custom repositories needed.
2. **SSH into the Green** and clone the repo into the local-addons folder:
   ```bash
   git clone <repo-url> /addons/wall-dashboard
   ```
3. **Create `/addons/wall-dashboard/.env`** with your real values (see `.env.example`):
   - `METRA_TOKEN` - bearer token from `gtfspublic.metrarr.com`
   - `NORTHBROOK_STOP_ID` and `CUS_STOP_ID` - resolve with `wall-dashboard stations <name>` on your dev machine
   - `NWS_LAT`, `NWS_LON` - defaults are correct for Northbrook
   - `NWS_USER_AGENT` - `wall-dashboard your-email@example.com` (NWS terms require a contact)
   - Leave `NWS_FORECAST_HOURLY_URL` blank for now
4. **Install from HA UI.** Settings -> Add-ons -> Add-on Store -> three-dot menu (top-right) -> Reload. "Wall Dashboard" appears under "Local add-ons." Click it -> Install. First build takes ~5 min on the Green's ARM64.
5. **Bootstrap the NWS URL** (one-time). SSH in:
   ```bash
   docker exec -it addon_wall_dashboard wall-dashboard bootstrap-nws
   ```
   Paste the printed `NWS_FORECAST_HOURLY_URL=...` line into your `.env`.
6. **Start the add-on.** Settings -> Add-ons -> Wall Dashboard -> Start. Watch the Log tab for "Application startup complete."
7. **Fire Stick.** Install Fully Kiosk Browser. Start URL: `http://<green-ip>:8765/`. Enable kiosk mode + boot autostart.

## Updates

```bash
ssh root@<green-ip>
cd /addons/wall-dashboard && git pull
```

Then in HA UI: Settings -> Add-ons -> Wall Dashboard -> "Rebuild." The Fire Stick refreshes itself every 30s.

## iOS widget

The widget lives at `scriptable/northbrook-trains.js`. Edit the `BASE_URL` constant
to your Green's LAN URL. The widget only refreshes when the phone is on home wifi
(LAN-only by default). To add cellular reach: Nabu Casa, Cloudflare Tunnel, or Tailscale.
