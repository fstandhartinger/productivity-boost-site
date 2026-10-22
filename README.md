# productivity-boost.com — Florian Standhartinger's AI lab

Calm, bilingual (EN at `/`, DE at `/de/`) company site: Decision Models and REAX first, built-in-public posts, earlier work
with the images from the old florianstandhartinger.com, about, contact, Impressum + Datenschutz (German).

- `src/content.py` — all copy (EN + DE); `src/build.py` — generator (writes `site/` + `nginx.conf` with CSP hashes).
- `src/data/posts.json` — X posts (views from api.fxtwitter.com, rounded down); `src/data/img.json` — image manifest.
- `tools/assets_r2.py`, `tools/xposts_r2.py` — AVIF/WebP pipeline; `tools/og_r2.py` — OG images; `tools/shots_r2.py` — screenshot matrix.
- Served by nginx on 8080 (`/healthz`). Preview: https://productivity-boost.app.mintapis.com (noindex on the preview host).
