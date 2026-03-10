# ED-Agent

A fully playable **Everdell** board game implementation with LAN multiplayer, local AI opponents, and a self-play reinforcement learning training pipeline.

## What is this?

ED-Agent brings the beloved woodland board game Everdell to your browser. Play against friends on your local network or challenge AI opponents running entirely on your own hardware — no cloud APIs, no subscriptions.

### Features

- **Complete Everdell rules** — All 48 unique cards (128 in deck), 4 seasons, worker placement, paired construction, events, journey locations, and full scoring with tiebreakers
- **LAN multiplayer** — Create a game, share the link, play from any device on your network (2-4 players)
- **AI opponents** — Three difficulty tiers (Apprentice / Journeyman / Master) with two backends:
  - **RL Agent** — Trained via self-play PPO, <1ms per move, no external dependencies
  - **LLM Agent** — Ollama-powered with difficulty-specific personas (fallback)
- **Real-time updates** — Server-Sent Events keep all players in sync
- **Move analysis** — Debug panel shows AI evaluation of your moves (Brilliant / Good / Inaccuracy / Mistake / Blunder)
- **AI chat assistant** — In-game rules Q&A accessible via `?` hotkey
- **Player stats** — ELO ratings, game history, leaderboards, and performance analytics
- **Self-play training** — Full RL training pipeline with progress monitoring via CLI and API

## Architecture

```
┌─────────────┐     SSE      ┌──────────────┐
│   ed-ui     │◄─────────────│  ed-engine   │
│  Vue 3 +    │─── REST ────►│  FastAPI     │
│  Vite       │              │  Game Logic  │
│  :5174      │              │  :4242       │
└─────────────┘              └──────┬───────┘
                                    │ REST
                             ┌──────▼───────┐
                             │   ed-ai      │
                             │  RL Agent    │──► PyTorch (CPU, <1ms/move)
                             │  :4243       │──► Ollama (optional fallback)
                             └──────────────┘
```

| Service | Stack | Purpose |
|---------|-------|---------|
| **ed-engine** | Python 3.11, FastAPI | Game rules engine, REST API, SSE events, player database, scoring |
| **ed-ui** | Vue 3, Vite, Pinia | Browser-based game interface with keyboard shortcuts |
| **ed-ai** | Python 3.11, FastAPI, PyTorch | AI opponent (RL self-play + Ollama fallback) |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Optional: [Ollama](https://ollama.ai) for LLM fallback (the RL agent needs no external service)

### Run

```bash
docker compose up --build
```

Then open **http://localhost:5174** in your browser.

### Play on LAN

Other devices on your network can join at `http://<your-ip>:5174`. Create a game in the lobby and share the game link.

## AI System

### Reinforcement Learning Agent (Primary)

The RL agent is trained via self-play using PPO (Proximal Policy Optimization) with action masking. It learns Everdell strategy from scratch by playing millions of games against itself.

| Property | Value |
|----------|-------|
| Architecture | Actor-critic MLP (512 → 256 → policy + value heads) |
| Parameters | ~393K |
| State encoding | 405-float tensor (resources, city, hand, opponents, meadow, events, locations) |
| Action space | 201 discrete actions with binary masking for legal moves |
| Inference time | <1ms per move (CPU) |
| Training method | PPO + GAE + self-play with multiprocessing |

#### Difficulty Tiers

| Tier | Source | Temperature | Behavior |
|------|--------|-------------|----------|
| Apprentice | Early checkpoint (~1K batches) | 1.5 | Plausible but exploratory moves |
| Journeyman | Mid checkpoint (~5K batches) | 1.0 | Competent play |
| Master | Full training (~50K batches) | 0.3 | Near-greedy VP maximization |

#### Training

```bash
# Full training run (CLI)
cd ed-ai
python -m ed_ai.rl.train --batches 10000 --games-per-batch 64 --workers 8

# Quick smoke test
python -m ed_ai.rl.train --batches 10 --games-per-batch 4 --workers 1

# Resume from checkpoint
python -m ed_ai.rl.train --resume models/checkpoint_005000.pt --batches 5000
```

Training can also be triggered via the API:
- `POST /rl/train` — Start training in background thread
- `GET /rl/status` — Current training status + available checkpoints
- `GET /rl/progress?last_n=50` — Recent training metrics
- `POST /rl/cancel` — Cancel active training

Progress is written to `ed-ai/models/training_status.json` and `training_progress.jsonl` for monitoring.

### LLM Agent (Fallback)

If no RL checkpoint is available, the AI falls back to Ollama with difficulty-specific system prompts. Requires Ollama running locally with a model like `qwen2.5-coder:7b`.

### Heuristic Agent (Last Resort)

A rule-based fallback that prioritizes: resolve choices → claim events → play high-value cards → place workers → prepare for season.

## Game Implementation

### Cards (48 unique, 128 in deck)

All cards from the base game are implemented with full special abilities:

- **Tan Travelers** — Immediate effects on play
- **Green Production** — Triggered during Prepare for Season
- **Red Destinations** — Worker placement slots on cards
- **Blue Governance** — Triggered when any card is played
- **Purple Prosperity** — Bonus scoring at end of game

### Locations

- **8 Basic locations** — Resource gathering (exclusive and shared)
- **11 Forest locations** — 3-4 randomly chosen per game, with interactive choices
- **Haven** — Shared, discard cards for resources
- **4 Journey locations** — Autumn only, discard cards for VP

### Events

- **4 Basic events** — Always available (3+ of each card type)
- **16 Special events** — 4 randomly chosen per game, require specific card pairs
- Events verified against physical card scans

### Scoring

Full end-game scoring with breakdown:
- Base card points + bonus card effects (purple prosperity)
- Event points (basic + special, including variable VP events)
- Journey points
- Point tokens (from Chapel, locations, etc.)
- Tiebreaker: event count → leftover resources

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `?` | Toggle help panel (rules + AI chat) |
| `` ` `` | Toggle debug panel (move evaluation, AI suggestions) |

## Player Stats & ELO

Players are tracked with an ELO rating system:

| Title | Rating |
|-------|--------|
| Seedling | 0+ |
| Wanderer | 1000+ |
| Forager | 1200+ |
| Ranger | 1400+ |
| Elder | 1600+ |

Access via the Leaderboard and Profile views, or the `/api/v1/players/leaderboard` API endpoint.

## Simulation & Testing

```bash
# Headless bot-vs-bot simulation (engine validation)
cd ed-engine && python tools/simulate.py --games 1000 --players 2

# Run tests
cd ed-engine && pytest
cd ed-ai && pytest
cd ed-ui && npm test

# Audit card special rules
cd ed-engine && python tools/audit_special_rules.py
```

## API Reference

### Engine (`ed-engine`, port 4242)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/games` | GET | List all games |
| `/api/v1/games` | POST | Create new game |
| `/api/v1/games/{id}` | GET | Get game state (with player perspective filtering) |
| `/api/v1/games/{id}/join` | POST | Join as player |
| `/api/v1/games/{id}/action` | POST | Submit action |
| `/api/v1/games/{id}/events` | GET | SSE stream for real-time updates |
| `/api/v1/players/leaderboard` | GET | ELO rankings |

### AI (`ed-ai`, port 4243)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/join` | POST | AI joins a game (starts playing in background) |
| `/think` | POST | One-shot: given state, return action |
| `/evaluate` | POST | Evaluate move quality |
| `/chat` | POST | Rules Q&A |
| `/health` | GET | Service health + Ollama status |
| `/rl/status` | GET | RL model info + training status |
| `/rl/train` | POST | Start training (background) |
| `/rl/cancel` | POST | Cancel active training |
| `/rl/progress` | GET | Recent training metrics |

## Development

```bash
# Engine (with hot reload)
cd ed-engine && pip install -e ".[dev]" && uvicorn ed_engine.app:app --reload --port 4242

# UI (with hot reload)
cd ed-ui && npm install && npm run dev

# AI (with hot reload)
cd ed-ai && pip install -e ".[dev]" && uvicorn ed_ai.app:app --reload --port 4243

# RL training (standalone, no Docker needed)
cd ed-ai && python -m ed_ai.rl.train --batches 100 --games-per-batch 8 --workers 4
```

## Project Structure

```
ed-agent/
├── ed-engine/              # Game rules engine
│   ├── ed_engine/
│   │   ├── engine/         # Core: game_manager, actions, scoring, seasons, events, locations
│   │   ├── models/         # Pydantic models: player, game, card, resources, enums
│   │   ├── cards/          # All 48 card implementations (constructions + critters)
│   │   └── api/            # FastAPI routes
│   └── tools/              # Simulation, audit, reconciliation scripts
├── ed-ai/                  # AI opponent service
│   ├── ed_ai/
│   │   ├── rl/             # Reinforcement learning module
│   │   │   ├── state_encoder.py   # Game state → 405-float tensor
│   │   │   ├── action_encoder.py  # 201-slot action space + masking
│   │   │   ├── network.py         # Actor-critic MLP (~393K params)
│   │   │   ├── ppo_agent.py       # PPO algorithm (GAE, clipped surrogate)
│   │   │   ├── self_play.py       # Headless game runner (multiprocessing)
│   │   │   ├── train.py           # Training orchestrator (CLI + API)
│   │   │   ├── checkpoint.py      # Model save/load + tier mapping
│   │   │   └── evaluate.py        # Evaluation vs baselines
│   │   ├── prompts/        # LLM personas + state serializer
│   │   ├── agent.py        # AIPlayer (RL → Ollama → heuristic fallback chain)
│   │   ├── app.py          # FastAPI service
│   │   └── parser.py       # LLM response parsing
│   └── models/             # Trained model checkpoints (gitignored)
├── ed-ui/                  # Vue 3 browser UI
│   └── src/
│       ├── components/     # GameBoard, PlayerCity, MeadowDisplay, ActionBar, etc.
│       └── views/          # GameView, LobbyView, LeaderboardView, ProfileView, ScoreView
└── docs/                   # Everdell rulebook PDF
```

## License

MIT
