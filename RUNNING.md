# How to Run MLDoctor

MLDoctor is a reproducible-training debugger: it reproduces a broken training script, investigates the cause, proposes a patch, and verifies the fix across real runs.

This guide covers every way to run the website/dashboard on your own computer.

---

## Option 1 — Docker (easiest, recommended)

You only need Docker installed. No Python or Node setup is required.

### 1. Build the image

From the project root (the folder containing the `Dockerfile`):

```bash
docker build -t mldoctor .
```

### 2. Start the website

```bash
docker run --rm -p 8765:8765 mldoctor
```

Keep this terminal open. To stop the website, press `Ctrl+C`.

### 3. Find your login token

The server prints a one-time dashboard URL with a token when it starts:

```text
MLDoctor dashboard: http://127.0.0.1:8765/?token=YOUR_TOKEN
Mode: MOCK (no live calls). Keep this terminal open.
```

If you started the container in the background, read the same line from the logs:

```bash
docker ps                 # find the container id/name
docker logs <container>   # copy the ?token= URL from the first lines
```

### 4. Open the website

Open the printed URL in your browser:

```text
http://127.0.0.1:8765/?token=YOUR_TOKEN
```

The page saves the token for the session and removes it from the address bar. If you open `http://127.0.0.1:8765/` without a token, paste the token from the server output into the token box on the page.

> The token changes every time the server restarts. Always use the URL from the latest start.

### Using Docker Compose instead

```bash
docker compose up --build
docker compose logs mldoctor   # in a second terminal: copy the ?token= URL
```

Stop it with:

```bash
docker compose down
```

---

## Option 2 — One process, no Docker

You need Python 3.11+ only. The frontend is prebuilt and served by the backend.

```bash
python -m venv .venv
.venv/bin/pip install ".[fixtures]"
.venv/bin/mldoctor serve --port 8765
```

Open the `http://127.0.0.1:8765/?token=...` URL printed in the terminal.

## Option 3 — Two processes, for frontend development

You need Python 3.11+ and Node 20.9+.

Terminal 1 — backend API:

```bash
MLDOCTOR_DEV_CORS=1 .venv/bin/mldoctor serve --port 8765
```

Terminal 2 — frontend with hot reload:

```bash
cd web
npm install
npm run dev
```

Open the frontend in your browser, pasting in the token printed by terminal 1:

```text
http://localhost:3000/?token=YOUR_TOKEN
```

---

## Using the dashboard

1. Pick a bundled fixture (for example `fixtures/repro.py`) or use **Paste my own code** to supply your own training script.
2. Set the baseline runs (`-k`) and, optionally, the verification run count.
3. Leave **Live model** off for the default simulated (MOCK) mode, or enable it only if the server was started with live model settings configured.
4. Click **Run pipeline** and watch the stages: Reproduce → Classify → Investigate → Patch → Verify.
5. When verification finishes you can download the HTML report, the proof bundle (`.json`), and the verified patch (`.patch`, apply it with `git apply mldoctor.patch`).

Every number on the page comes from a real server event. A `FAIL` / `REJECTED` verdict is a real result: the patch did not verify.

> **Warning:** pasted scripts and any script you run execute locally with your operating-system user. Only run scripts you trust, and never paste secrets into them.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Page asks for a token | Copy the `?token=` value from the latest server start (terminal or `docker logs`). Tokens change on every restart. |
| `401` errors in the page | Same as above — the token is stale. Re-open the freshly printed URL. |
| Port 8765 already in use | Stop the other process, or start on another port: `mldoctor serve --port 8766` (Docker: `-p 8766:8765`). |
| Container starts but the page will not load | Check `docker logs <container>` for the dashboard line, and confirm the port mapping with `docker ps`. |
| Live model toggle is disabled | The server was not started with `MLDOCTOR_BASE_URL`, `MLDOCTOR_MODEL`, and `MLDOCTOR_API_KEY` set. MOCK mode works without them. |
| Health check | `GET /` returns the dashboard; `GET /api/state` returns `401` without a token and `200` with one. |

## For developers

```bash
cd web && npx tsc --noEmit && npx eslint . && npx vitest run && npm run build && npm run build:copy
.venv/bin/python -m pytest -q
```

Rebuild the bundled frontend after changing `web/` with `npm run build:copy`, which refreshes `src/mldoctor/static_next/`.
