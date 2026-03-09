# ED-Agent

A fully playable **Everdell** board game implementation with LAN multiplayer and a local AI opponent powered by Ollama.

## What is this?

ED-Agent brings the beloved woodland board game Everdell to your browser. Play against friends on your local network or challenge an AI opponent running entirely on your own hardware — no cloud APIs, no subscriptions.

### Features

- **Complete Everdell rules** — All 128 cards (Critters + Constructions), 4 seasons, worker placement, events, and scoring
- **LAN multiplayer** — Create a game, share the link, play from any device on your network
- **Local AI opponent** — Three difficulty levels powered by Ollama (runs on your hardware)
- **Real-time updates** — Server-Sent Events keep all players in sync
- **Move analysis** — Optional debug panel shows AI evaluation of your moves (chess-style quality ratings)
- **Player stats** — ELO ratings, game history, leaderboards, and performance analytics

## Architecture

```
┌─────────────┐     SSE      ┌──────────────┐
│   ed-ui     │◄─────────────│  ed-engine   │
│  Vue 3 +    │─── REST ────►│  FastAPI     │
│  Vite       │              │  Game Logic  │
│  :5174      │              │  :4242       │
└─────────────┘              └──────┬───────┘
                                    │ REST
                             ┌──────▼───────┐     HTTP     ┌─────────┐
                             │   ed-ai      │─────────────►│ Ollama  │
                             │  AI Agent    │              │ :11434  │
                             │  :4243       │              └─────────┘
                             └──────────────┘
```

| Service | Stack | Purpose |
|---------|-------|---------|
| **ed-engine** | Python 3.11, FastAPI | Game rules engine, REST API, SSE events, player database |
| **ed-ui** | Vue 3, Vite, Pinia | Browser-based game interface |
| **ed-ai** | Python 3.11, FastAPI | AI opponent using local Ollama models |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- [Ollama](https://ollama.ai) installed with a model pulled (e.g., `ollama pull phi4:14b`)

### Run

```bash
docker compose up --build
```

Then open **http://localhost:5174** in your browser.

### Play on LAN

Other devices on your network can join at `http://<your-ip>:5174`. Create a game in the lobby and share the game link.

## AI Difficulty

| Level | Persona | Style |
|-------|---------|-------|
| Apprentice | Friendly teacher | Simple heuristics, explains its reasoning |
| Journeyman | Balanced player | Solid fundamentals, adapts to game state |
| Master | Ruthless optimizer | Considers opponent state, maximizes efficiency |

The AI runs entirely on your local hardware via Ollama. No data leaves your network.

## Development

```bash
# Engine only (with hot reload)
cd ed-engine && pip install -e ".[dev]" && uvicorn ed_engine.app:app --reload --port 4242

# UI only (with hot reload)
cd ed-ui && npm install && npm run dev

# AI only
cd ed-ai && pip install -e ".[dev]" && uvicorn ed_ai.app:app --reload --port 4243

# Run tests
cd ed-engine && pytest
cd ed-ai && pytest
cd ed-ui && npm test
```

## Game Rules Reference

The full Everdell rulebook is included at `docs/89-everdell-rulebook.pdf` for development reference.

## License

MIT
