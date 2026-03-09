import type { GameState, ValidAction } from '../types'

const BASE = '/api/v1'

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
