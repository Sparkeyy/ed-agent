import { defineStore } from 'pinia'
import { ref } from 'vue'
import { SSEManager } from '../api/sse'
import * as api from '../api/client'

export interface Player {
  id: string
  name: string
  resources: Record<string, number>
  city: unknown[]
  hand: unknown[]
  workers: number
}

export interface GameAction {
  type: string
  payload?: Record<string, unknown>
}

export const useGameStore = defineStore('game', () => {
  const gameId = ref<string | null>(null)
  const players = ref<Player[]>([])
  const currentPlayerIdx = ref(0)
  const meadow = ref<unknown[]>([])
  const myPlayerId = ref<string | null>(null)
  const validActions = ref<GameAction[]>([])
  const connected = ref(false)

  let sse: SSEManager | null = null

  function handleEvent(event: string, data: unknown) {
    const d = data as Record<string, unknown>
    switch (event) {
      case 'state':
        if (d.players) players.value = d.players as Player[]
        if (d.currentPlayerIdx !== undefined) currentPlayerIdx.value = d.currentPlayerIdx as number
        if (d.meadow) meadow.value = d.meadow as unknown[]
        if (d.validActions) validActions.value = d.validActions as GameAction[]
        break
      case 'action':
        // Re-fetch full state on action events
        if (gameId.value) {
          api.getGameState(gameId.value).then((state) => {
            handleEvent('state', state)
          })
        }
        break
    }
  }

  function connect(id: string) {
    gameId.value = id
    sse = new SSEManager(id, handleEvent)
    sse.connect()
    connected.value = true
  }

  function disconnect() {
    if (sse) {
      sse.disconnect()
      sse = null
    }
    connected.value = false
    gameId.value = null
  }

  async function performAction(action: GameAction) {
    if (!gameId.value) return
    await api.performAction(gameId.value, action)
  }

  return {
    gameId,
    players,
    currentPlayerIdx,
    meadow,
    myPlayerId,
    validActions,
    connected,
    connect,
    disconnect,
    performAction,
  }
})
