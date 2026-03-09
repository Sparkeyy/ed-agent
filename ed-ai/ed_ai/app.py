from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ed_ai.agent import AIAgent

app = FastAPI(title="ed-ai", version="0.1.0")
agent = AIAgent()


class ThinkRequest(BaseModel):
    game_state: dict
    persona: str = "journeyman"


class ThinkResponse(BaseModel):
    action: dict
    reasoning: str = ""
    retries: int = 0


class EvaluateRequest(BaseModel):
    game_state: dict
    action: dict


class EvaluateResponse(BaseModel):
    quality: float = Field(ge=0.0, le=1.0)
    explanation: str = ""


@app.post("/think", response_model=ThinkResponse)
async def think(req: ThinkRequest) -> ThinkResponse:
    result = await agent.think(req.game_state, persona=req.persona)
    return ThinkResponse(**result)


@app.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(req: EvaluateRequest) -> EvaluateResponse:
    result = await agent.evaluate(req.game_state, req.action)
    return EvaluateResponse(**result)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "ed-ai"}
