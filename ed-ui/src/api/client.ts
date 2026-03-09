const BASE_URL = import.meta.env.VITE_API_URL || '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`)
  }
  return res.json()
}

export interface CreateGameRequest {
  playerName: string
  numPlayers: number
}

export interface JoinGameRequest {
  playerName: string
}

export interface GameState {
  id: string
  players: unknown[]
  currentPlayerIdx: number
  meadow: unknown[]
  validActions: unknown[]
  status: string
}

export interface GameAction {
  type: string
  payload?: Record<string, unknown>
}

export function createGame(data: CreateGameRequest) {
  return request<{ gameId: string }>('/games', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function joinGame(gameId: string, data: JoinGameRequest) {
  return request<{ playerId: string }>(`/games/${gameId}/join`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function getGameState(gameId: string) {
  return request<GameState>(`/games/${gameId}`)
}

export function performAction(gameId: string, action: GameAction) {
  return request<{ ok: boolean }>(`/games/${gameId}/action`, {
    method: 'POST',
    body: JSON.stringify(action),
  })
}

export function getPlayers(gameId: string) {
  return request<{ players: unknown[] }>(`/games/${gameId}/players`)
}
