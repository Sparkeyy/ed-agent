# ED-Agent — Everdell Board Game

LAN multiplayer Everdell with local AI opponent (Ollama).

## Architecture

Three services in a monorepo:

| Service | Port | Stack | Purpose |
|---------|------|-------|---------|
| ed-engine | 4242 | Python 3.11 + FastAPI | Game engine, rules, API |
| ed-ui | 5174 | Vue 3 + Vite | Browser UI |
| ed-ai | 4243 | Python 3.11 + FastAPI | AI opponent via Ollama |

## Key Conventions

- **Card implementations**: One file per card in `ed-engine/ed_engine/cards/`. Use `@register` decorator.
- **Card types**: TAN (Traveler), GREEN (Production), RED (Destination), BLUE (Governance), PURPLE (Prosperity)
- **Card categories**: CRITTER or CONSTRUCTION. Each critter pairs with a construction.
- **Game state**: Pydantic models in `ed-engine/ed_engine/models/`. GameState is the single source of truth.
- **API**: REST + SSE. All game mutations go through POST /api/v1/games/{id}/action.
- **SSE events**: Unidirectional server→client. Client sends actions via REST, receives state updates via SSE.
- **AI**: Ollama on host (port 11434). AI serializes game state to compact text, asks model for action, parses response.
- **Tests**: pytest (engine, ai), vitest (ui). Every card ability must have a test.

## Running

```bash
docker compose up --build    # All services
docker compose up ed-engine  # Engine only (for testing)
```

## Rulebook

Reference PDF at `docs/89-everdell-rulebook.pdf`. All 128 cards and special rules are defined there.

## Beads

Issues tracked with prefix `ed-`. Use `bd` commands.
