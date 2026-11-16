# Strigoi Aether Map website

Static HTML/CSS/JavaScript, published from this folder with GitHub Pages.
Brazilian Portuguese, US English, and Latin American Spanish with localized
app screenshots, versioned downloads, and installer terms.
Share a direct Spanish link by adding `?lang=es-419` before any page anchor. No build or account required to read the site.

Preview from the repository root:

```sh
python -m http.server 8768 --directory website
```

Open http://127.0.0.1:8768/. Publishing instructions: `docs/PUBLISHING.md`.
The original site code uses GPLv3; bundled app screenshots and map imagery
retain their respective rights and third-party notices.

Edit the Live Sync setup guides in [PT-BR](live-sync.md), [EN-US](live-sync.en-US.md), or [ES-419](live-sync.es-419.md). Run
`./scripts/render-live-sync-guide.ps1` from the repository root to update its static HTML page.
