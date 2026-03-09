import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { SSEManager } from '../api/sse'
import * as api from '../api/client'
import type { GameState, ValidAction, PlayerData, CardData } from '../types'

const STORAGE_KEY = 'everdell_session'

interface StoredSession {
  gameId: string
  playerToken: string
  myPlayerId: string
}

export const useGameStore = defineStore('game', () => {
  // Connection state
  const gameId = ref<string | null>(null)
  const playerToken = ref<string | null>(null)
  const myPlayerId = ref<string | null>(null)
  const connected = ref(false)
  const error = ref<string | null>(null)
  const loading = ref(false)

  // Game state
  const state = ref<GameState | null>(null)

  // SSE instance (not reactive)
  let sse: SSEManager | null = null

  // Computed
  const myPlayer = computed<PlayerData | undefined>(
    () => state.value?.players.find(p => p.id === myPlayerId.value),
  )
  const currentPlayer = computed<PlayerData | undefined>(
    () => state.value?.players.find(p => p.id === state.value?.current_player_id),
  )
  const isMyTurn = computed<boolean>(
    () => myPlayerId.value != null && myPlayerId.value === state.value?.current_player_id,
  )
  const validActions = computed<ValidAction[]>(
    () => state.value?.valid_actions ?? [],
  )
  const meadow = computed<CardData[]>(
    () => state.value?.meadow ?? [],
  )
  const gameOver = computed<boolean>(
    () => state.value?.game_over ?? false,
  )
  const opponents = computed<PlayerData[]>(
    () => state.value?.players.filter(p => p.id !== myPlayerId.value) ?? [],
  )

  // Session persistence
  function saveSession(): void {
    if (!gameId.value || !playerToken.value || !myPlayerId.value) return
    const session: StoredSession = {
      gameId: gameId.value,
      playerToken: playerToken.value,
      myPlayerId: myPlayerId.value,
    }
    localStorage.setItem(`${STORAGE_KEY}_${gameId.value}`, JSON.stringify(session))
  }

  function loadSession(id?: string): boolean {
    const targetId = id ?? gameId.value
    if (!targetId) return false
    const raw = localStorage.getItem(`${STORAGE_KEY}_${targetId}`)
    if (!raw) return false
    try {
      const session: StoredSession = JSON.parse(raw)
      gameId.value = session.gameId
      playerToken.value = session.playerToken
      myPlayerId.value = session.myPlayerId
      return true
    } catch {
      return false
    }
  }

  // SSE event handler
  function handleSSEEvent(event: string, data: any): void {
    switch (event) {
      case 'connected':
        connected.value = true
        break
      case 'game_state':
        if (data && typeof data === 'object') {
          state.value = data as GameState
        }
        break
      case 'player_joined':
      case 'game_started':
        refreshState()
        break
      case 'game_over':
        if (data && typeof data === 'object') {
          state.value = data as GameState
        }
        break
    }
  }

  function connectSSE(): void {
    if (!gameId.value || !playerToken.value) return
    if (sse) {
      sse.disconnect()
    }
    sse = new SSEManager(gameId.value, playerToken.value, handleSSEEvent)
    sse.connect()
    connected.value = true
  }

  // Actions
  async function createNewGame(playerCount: number, name: string): Promise<string> {
    loading.value = true
    error.value = null
    try {
      const resp = await api.createGame(playerCount, name)
      gameId.value = resp.game_id
      playerToken.value = resp.player_token
      myPlayerId.value = resp.player_id
      saveSession()
      return resp.game_id
    } catch (e: any) {
      error.value = e.message ?? 'Failed to create game'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function joinExistingGame(id: string, name: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const resp = await api.joinGame(id, name)
      gameId.value = id
      playerToken.value = resp.player_token
      myPlayerId.value = resp.player_id
      saveSession()
    } catch (e: any) {
      error.value = e.message ?? 'Failed to join game'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function submitAction(action: ValidAction): Promise<void> {
    if (!gameId.value || !playerToken.value) return
    loading.value = true
    error.value = null
    try {
      const newState = await api.performAction(gameId.value, playerToken.value, action)
      state.value = newState
    } catch (e: any) {
      error.value = e.message ?? 'Action failed'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function refreshState(): Promise<void> {
    if (!gameId.value || !playerToken.value) return
    try {
      const newState = await api.getGameState(gameId.value, playerToken.value)
      state.value = newState
    } catch (e: any) {
      error.value = e.message ?? 'Failed to refresh state'
    }
  }

  function disconnect(): void {
    if (sse) {
      sse.disconnect()
      sse = null
    }
    connected.value = false
    state.value = null
    error.value = null
  }

  return {
    // Connection state
    gameId,
    playerToken,
    myPlayerId,
    connected,
    error,
    loading,

    // Game state
    state,

    // Computed
    myPlayer,
    currentPlayer,
    isMyTurn,
    validActions,
    meadow,
    gameOver,
    opponents,

    // Actions
    createNewGame,
    joinExistingGame,
    connectSSE,
    submitAction,
    refreshState,
    disconnect,
    saveSession,
    loadSession,
  }
})
