# OpenManus + Kai Integration

> Run OpenManus as an MCP server so Kai discovers its tools — web browsing,
> shell execution, and file editing — as first-class native tools on every
> Kai platform (Android, iOS, Web, Desktop).

---

## How it works

```
┌─────────────────────────────────────────────────────────────────────┐
│  Kai (any platform)                                                 │
│                                                                     │
│  Settings > Tools > MCP Servers > "OpenManus"                      │
│       │                                                             │
│       │  Streamable HTTP  (POST /mcp, SSE responses)               │
│       ▼                                                             │
│  McpClient ──────────────────────────────────────────────────────► │
└──────────────────────────────────────────┬──────────────────────────┘
                                           │
                   http://localhost:8765/mcp
                                           │
                                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│  OpenManus MCP Server  (openmanus/mcp_server.py)                    │
│                                                                      │
│  Tools registered:                                                   │
│    • bash          — run shell commands                              │
│    • browser       — navigate and scrape web pages                  │
│    • editor        — read / write / patch files                      │
│    • terminate     — signal task completion                          │
└──────────────────────────────────────────────────────────────────────┘
```

The [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) is the
bridge — no Kotlin or Python code needs to cross the language boundary.

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.10 + |
| pip | any recent |
| Playwright browsers | installed via `playwright install` |
| An LLM API key | OpenAI, Anthropic, Gemini, Ollama, … |

---

## Quick start (local)

### 1 — Clone OpenManus into the `openmanus/src` directory

```bash
git clone https://github.com/hamadnao718-cyber/OpenManus openmanus/src
```

### 2 — Create a virtual environment and install dependencies

```bash
cd openmanus
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 3 — Configure your LLM API key

**Option A — environment variables (recommended for Docker):**

```bash
cp .env.example .env
# Edit .env and set OPENMANUS_API_KEY, OPENMANUS_MODEL, etc.
```

`mcp_server.py` reads these variables at startup and generates
`config/config.toml` automatically when the file does not exist.

**Option B — config file:**

```bash
cp config/config.example.toml config/config.toml
# Edit config/config.toml and fill in your API key
```

### 4 — Start the MCP server

```bash
python mcp_server.py
# Server listening on http://0.0.0.0:8765/mcp
```

Pass `--host` / `--port` to customise the bind address:

```bash
python mcp_server.py --host 127.0.0.1 --port 9000
```

### 5 — Connect Kai

1. Open Kai → **Settings** → **Tools** → **Add MCP Server**
2. Name: `OpenManus`
3. URL: `http://localhost:8765/mcp`
4. Tap **Add** — Kai connects and discovers the tools automatically

The tools (`bash`, `browser`, `editor`, `terminate`) appear inside the
OpenManus server card and are immediately available to the AI.

---

## Docker Compose (Kai Web + OpenManus)

The included `docker-compose.yml` at the repository root runs both services:

```bash
# From the Kai repository root:
cp openmanus/.env.example openmanus/.env
# Edit openmanus/.env — set OPENMANUS_API_KEY at minimum

docker compose up
```

| Service | URL |
|---------|-----|
| Kai Web app | http://localhost:8080 |
| OpenManus MCP server | http://localhost:8765/mcp |

Inside Kai Web, add the MCP server URL as
`http://openmanus-mcp:8765/mcp` (the Docker internal hostname).

---

## Environment variables reference

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENMANUS_API_KEY` | *(required)* | LLM provider API key |
| `OPENMANUS_API_BASE_URL` | `https://api.openai.com/v1` | LLM base URL |
| `OPENMANUS_MODEL` | `gpt-4o` | Model ID |
| `OPENMANUS_HOST` | `0.0.0.0` | Bind host |
| `OPENMANUS_PORT` | `8765` | Bind port |

---

## Available tools

| Tool | Description |
|------|-------------|
| `bash` | Execute a shell command and return its stdout/stderr |
| `browser` | Navigate to a URL, click elements, extract page content |
| `editor` | Read, write, or apply str-replace patches to local files |
| `terminate` | Signal that the agent has finished its task |

---

## Connecting via the Autonomous Heartbeat

Kai's [heartbeat](features/heartbeat.md) runs a background self-check every
30 minutes. When OpenManus is connected as an MCP server, the heartbeat
prompt can include instructions that leverage OpenManus tools — for example,
periodically checking a URL, running a shell script, or summarising a file.

Edit the custom heartbeat prompt in **Settings → Heartbeat → Custom prompt**
to instruct the AI to use `bash` or `browser` tools as part of its routine.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'app'`**
Ensure you cloned OpenManus into `openmanus/src/` (step 1 above) and that
you are running `mcp_server.py` from the `openmanus/` directory.

**CORS errors in Kai Web**
The FastMCP HTTP server does not add CORS headers by default. Run Kai Web
and the MCP server on the same origin, or add a reverse-proxy (e.g. Nginx)
that injects the necessary CORS headers.

**Browser automation not working inside Docker**
The Docker Compose service runs Chromium in headless mode. Ensure the
container has the `--no-sandbox` flag set (already included in the provided
`docker-compose.yml`).
