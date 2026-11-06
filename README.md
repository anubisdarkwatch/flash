# Flash Station

Browser installer for Anubis Darkwatch firmware: pick your board, click **Install**, choose the port. Built on
[ESP Web Tools](https://esphome.github.io/esp-web-tools/) and served by GitHub Pages.

Works in Chrome or Edge on desktop (Web Serial). Not on iPhone / iPad.

## How it updates itself
- `boards.json` lists every board: its project repo, the `.bin` name prefix, chip family, photo and card text.
- `.github/workflows/sync-firmware.yml` runs daily (or **Actions → Sync firmware → Run workflow**). It clones each
  project repo, and `tools/sync.py` copies the newest `firmware/<prefix>-v<version>.bin` into `firmware/`, writes
  `manifests/<board>.json`, and updates `firmware.json` (version, size, SHA-256, date). Then it commits if anything changed.
- So shipping a new version is: push the new `.bin` to the project repo, then wait for the daily sync or run it by hand.

## Adding a board
Add an entry to `boards.json` (and a 720×450 photo in `img/`), then run the sync. `chip` must be an ESP Web Tools chip family
(`ESP32`, `ESP32-S3`, `ESP32-C3`, `ESP32-C5`, …). Every `.bin` must be a merged image flashed at offset 0.

## Run it locally
```
python3 tools/sync.py ../          # folder that holds the project repo checkouts
python3 -m http.server 8000        # then open http://localhost:8000 (localhost counts as secure for Web Serial)
```

## Custom domain
Add a `CNAME` file containing the domain (e.g. `flash.beatconductor.com`) and point a CNAME DNS record at
`anubisdarkwatch.github.io`. Then tick **Enforce HTTPS** under Settings → Pages.

MIT license.
