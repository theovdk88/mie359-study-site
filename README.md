# MIE359 Study Site

This site renders the chapter markdown files in `/Users/theov/Documents/3.2/MIE359/mie359_codex_bundle/chapters` as the primary visible study content.

## Build the deployable static site

```bash
cd /Users/theov/Documents/3.2/MIE359/study-site
python3 build.py && python3 export_static.py
```

This generates the Cloudflare Pages-ready output in:

```text
/Users/theov/Documents/3.2/MIE359/study-site/dist
```

## Run locally

```bash
cd /Users/theov/Documents/3.2/MIE359/study-site
python3 -m http.server 8000
```

Open:

```text
http://localhost:8000
```

## Cloudflare Pages settings

- Build command: `python3 build.py && python3 export_static.py`
- Build output directory: `dist`

## Terminal deployment

Preferred Cloudflare Pages terminal deploy:

```bash
cd /Users/theov/Documents/3.2/MIE359/study-site
python3 build.py && python3 export_static.py
npx wrangler pages deploy dist --project-name mie359-study-site
```

Compatibility fallback for environments currently calling `wrangler deploy`:

```bash
cd /Users/theov/Documents/3.2/MIE359/study-site
python3 build.py && python3 export_static.py
npx wrangler deploy
```

The fallback works because `wrangler.toml` now points `assets.directory` at `dist`, which satisfies the exact error shown when Cloudflare tried to deploy without a Worker entrypoint.
