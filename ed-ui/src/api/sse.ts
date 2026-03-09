const BASE = '/api/v1'
const MAX_RECONNECT_DELAY = 30_000

export type SSEHandler = (event: string, data: any) => void

export class SSEManager {
  private gameId: string
  private playerToken: string
  private handler: SSEHandler
  private source: EventSource | null = null
  private reconnectTimer: number | null = null
  private reconnectDelay = 1000

  constructor(gameId: string, playerToken: string, handler: SSEHandler) {
    this.gameId = gameId
    this.playerToken = playerToken
    this.handler = handler
  }

  connect(): void {
    this.disconnect()

    const url = `${BASE}/games/${this.gameId}/events?player_token=${encodeURIComponent(this.playerToken)}`
    this.source = new EventSource(url)

    const events = ['game_state', 'player_joined', 'game_started', 'game_over', 'connected']
    for (const eventName of events) {
      this.source.addEventListener(eventName, (ev) => {
        try {
          const data = JSON.parse((ev as MessageEvent).data)
          this.handler(eventName, data)
        } catch {
          // ignore parse errors
        }
      })
    }

    this.source.onopen = () => {
      this.reconnectDelay = 1000
    }

    this.source.onerror = () => {
      this.source?.close()
      this.source = null
      this.scheduleReconnect()
    }
  }

  disconnect(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.source) {
      this.source.close()
      this.source = null
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer !== null) return
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, MAX_RECONNECT_DELAY)
      this.connect()
    }, this.reconnectDelay)
  }
}
