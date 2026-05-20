# Wall Dashboard — TODO

## Now
- Install Advanced SSH & Web Terminal add-on on the Green and `git clone` into `/addons/wall-dashboard/`.
- Fill `.env` on the Green (Metra token, stop_ids, NWS User-Agent).
- Install add-on from HA UI ("Local add-ons"), start it.
- Point Fully Kiosk Browser on Fire Stick at `http://<green-ip>:8765/`.

## Done
- Python rewrite of the prior Google Apps Script dashboard.
- All four data sources ported and tested.
- iOS Scriptable widget retargeted to LAN endpoint.

## Later (post-deploy)
- Verify rendering on TV; tweak typography if needed.
- Add HA REST sensors for delay > N min push notifications (optional).
- Add Nabu Casa / Cloudflare Tunnel if iOS widget needs cellular reach.
