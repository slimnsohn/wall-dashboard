# Wall Dashboard — TODO

## Deployed and running
- Python service deployed as HA add-on on the Green at `http://192.168.4.65:8765/`.
- Fire Stick on HDMI 3 runs Fully Kiosk Browser auto-launched on boot.
- HA automations: TV on at 07:00 + switch to HDMI 3, off at 21:00.
- All four data sources live: Metra, Amtrak, NWS weather, Open-Meteo AQI + UV.

## Maybe-do later
- README "moving house" section: list every place the IP/subnet is hardcoded
  (Fire Stick start URL, `configuration.yaml` WoL host + broadcast, LG webOS
  pairing IP). Useful if the network changes.
- Smart HDMI handling: auto-return to HDMI 3 when Fire Cube goes idle during
  display hours. Requires HA Fire TV integration + idle-state detection.
- Switch Fire Stick start URL from raw IP to `homeassistant.local:8765`.
  Deferred because Fire OS mDNS is unreliable and DHCP reservation works.
- Empty-state polish on trains panel: late nights with no upcoming trains
  show an empty list under the header. Could add a "no upcoming trains" line.
- Add HA REST sensors for delay > N min push notifications if useful.
- Add Nabu Casa / Cloudflare Tunnel only if the iOS widget needs cellular reach.

## Won't do
- Re-enable Kiosk Mode in Fully Kiosk (locked the Fire Stick out once).
- Change WoL broadcast off `255.255.255.255` (won't work on the /22 subnet).
- Drop the WoL switch in favor of LG's `media_player.turn_on` (LG's is flaky).
- Disable Quick Start+ on the TV (breaks WoL).
