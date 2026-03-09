import type { GameState, ValidAction, PlayerProfile, LeaderboardEntry, MoveEvaluation } from '../types'

const BASE = '/api/v1'
const AI_BASE = 'http://localhost:4243'

export class ApiError extends Error {
  status: number
  statusText: string

  constructor(status: number, statusText: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.statusText = statusText
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body.detail) message = body.detail
      else if (body.error) message = body.error
      else if (body.message) message = body.message
    } catch {
      // no JSON body, use status text
    }
    throw new ApiError(res.status, res.statusText, message)
  }

  return res.json()
}

export interface CreateGameResponse {
  game_id: string
  player_token: string
  player_id: string
}

export interface JoinGameResponse {
  player_token: string
  player_id: string
}

interface GameStateResponse {
  state: GameState
}

export async function createGame(playerCount: number, creatorName: string): Promise<CreateGameResponse> {
  return request<CreateGameResponse>('/games', {
    method: 'POST',
    body: JSON.stringify({ player_count: playerCount, creator_name: creatorName }),
  })
}

export async function joinGame(gameId: string, playerName: string): Promise<JoinGameResponse> {
  return request<JoinGameResponse>(`/games/${gameId}/join`, {
    method: 'POST',
    body: JSON.stringify({ player_name: playerName }),
  })
}

export async function getGameState(gameId: string, playerToken: string): Promise<GameState> {
  const resp = await request<GameStateResponse>(
    `/games/${gameId}?player_token=${encodeURIComponent(playerToken)}`,
  )
  return resp.state
}

export async function performAction(gameId: string, playerToken: string, action: ValidAction): Promise<GameState> {
  const body: Record<string, unknown> = {
    player_token: playerToken,
    action_type: action.action_type,
  }
  if (action.location_id !== undefined) body.location_id = action.location_id
  if (action.card_name !== undefined) body.card_name = action.card_name
  if (action.source !== undefined) body.source = action.source
  if (action.meadow_index !== undefined) body.meadow_index = action.meadow_index
  if (action.use_paired_construction !== undefined) body.use_paired_construction = action.use_paired_construction

  const resp = await request<GameStateResponse>(`/games/${gameId}/action`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
  return resp.state
}

// Player profile
export async function getProfile(username: string): Promise<PlayerProfile> {
  return request<PlayerProfile>(`/players/${encodeURIComponent(username)}`)
}

// Leaderboard
export async function getLeaderboard(): Promise<LeaderboardEntry[]> {
  return request<LeaderboardEntry[]>('/leaderboard')
}

// Move evaluation (ed-ai service)
export async function evaluateMove(
  gameState: GameState,
  action: ValidAction,
  validActions: ValidAction[],
): Promise<MoveEvaluation> {
  const res = await fetch(`${AI_BASE}/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      game_state: gameState,
      action,
      valid_actions: validActions,
    }),
  })

  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (body.detail) message = body.detail
    } catch { /* no JSON body */ }
    throw new ApiError(res.status, res.statusText, message)
  }

  return res.json()
}
