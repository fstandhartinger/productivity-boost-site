# productivity-boost.com — Florian Standhartinger

"Self-portrait as a radio band": a static EN/DE personal site. Frequency = genre, time = rows; the hero waterfall is drawn
from `src/data/band.json` (every entry has a source).

- `src/` — generator (`build.py`), copy (`content.py`), CSS, JS (`band.js` renderer, `main.js` enhancement), data, legal texts.
- `tools/assets.py <media-dir>` — images, video loop, waterfall images, dot plot (needs ffmpeg + Playwright).
- `python3 -I src/build.py` — writes `site/` and `nginx.conf` (CSP hashes for the one inline script and style).
- Served by nginx on 8080 (`/healthz`). Preview: https://productivity-boost.app.mintapis.com (noindex on the preview host).
