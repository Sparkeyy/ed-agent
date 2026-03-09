from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ed_engine.api.games import router as games_router
from ed_engine.api.players import router as players_router

app = FastAPI(title="Ed-Engine", description="Everdell board game engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(games_router, prefix="/games", tags=["games"])
app.include_router(players_router, prefix="/players", tags=["players"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
