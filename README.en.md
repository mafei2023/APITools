# API Key Manager

[简体中文](README.md) | [English](README.en.md) | [繁体中文](README.zh-TW.md) | [日本語](README.ja.md)

A locally-run API key management tool for developers to batch import, group, test, and clean up API keys efficiently.

## Features

- **Batch Import** — Paste multiple keys at once, automatic deduplication, Base64-encoded keys auto-decoded
- **Group Management** — Organize keys by provider or use case, with custom group aggregation views
- **One-Click Testing** — Concurrent multi-thread key availability testing with latency and error details
- **Statistics Dashboard** — At-a-glance view of available / failed / total keys
- **Cleanup** — Quickly remove failed keys to keep your key pool clean
- **Light / Dark Theme** — Automatically follows system preference

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python / Flask |
| Frontend | Single-file HTML (vanilla JS, no framework) |
| Database | SQLite |
| API Protocol | OpenAI-compatible endpoints |

## Quick Start

### Prerequisites

- Python 3.9+

### Install & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python app.py
```

Then open http://localhost:5000 in your browser.

Windows users can also double-click `start.bat` to launch.

## Project Structure

```
APITools/
├── app.py              # Flask backend + API routes
├── index.html          # Single-page frontend app
├── data.db             # SQLite database (auto-created on first run)
├── requirements.txt    # Python dependencies
├── start.bat           # Windows quick-start script
├── PRODUCT.md          # Product definition
└── DESIGN.md           # Design specification
```

## Workflow

1. **Create Groups** — Set up groups by API provider (e.g. OpenAI, Claude) with protocol and model config
2. **Add Keys** — Batch-paste keys into groups; keys are automatically tested on add
3. **Check Status** — View global stats on the dashboard, or drill into individual key details per group
4. **Clean Up** — One-click removal of failed keys to keep things tidy

## Friends

- [LINUX DO](https://linux.do) — A Linux and open-source tech community

## License

MIT
