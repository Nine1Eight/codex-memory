# Looki Creator Studio

Looki is a dependency-free, local-first production and recording studio. It creates editable video plans, records camera and microphone input, captures browser speech-recognition captions where supported, adds chapter markers, persists project metadata, and exports real JSON, TXT, SRT, chapter, and media files.

## Run

Camera APIs require a secure context. Localhost is treated as secure by browsers:

```sh
python serve.py
```

Open <http://127.0.0.1:8080>. Opening `index.html` directly still supports planning and exports, but browsers usually block camera access on `file://` URLs.

## Privacy and storage

- Project plans, notes, transcripts, and markers are stored in browser local storage.
- Camera and microphone streams remain in the browser.
- Recorded media is held in memory and must be downloaded before closing the tab.
- Browser speech recognition availability and privacy behavior depend on the browser vendor. The UI does not claim it is on-device.
- No analytics, remote APIs, or third-party dependencies are included.

## Architecture

- `index.html` — semantic application shell
- `styles.css` — responsive UI and accessibility styles
- `app.js` — project, media, caption, persistence, and export logic
- `sw.js` / `manifest.webmanifest` — offline-capable PWA shell
- `serve.py` — zero-dependency local development server

## Production integration boundary

The repository does not bundle an AI model, wearable SDK, cloud sync service, or deployment credentials. Production AI planning and multimodal coaching should be connected behind an authenticated service or a separately distributed on-device model runtime. The current planner is deterministic and clearly operates without pretending to run a model.
