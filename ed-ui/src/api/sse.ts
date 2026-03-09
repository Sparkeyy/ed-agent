const BASE_URL = import.meta.env.VITE_API_URL || '/api'

export type SSEHandler = (event: string, data: unknown) => void

export class SSEManager {
  private gameId: string
  private handler: SSEHandler
  private source: EventSource | null = null

  constructor(gameId: string, handler: SSEHandler) {
    this.gameId = gameId
    this.handler = handler
  }

  connect() {
    this.disconnect()

    const url = `${BASE_URL}/games/${this.gameId}/events`
    this.source = new EventSource(url)

    this.source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        this.handler('state', data)
      } catch {
        // ignore parse errors
      }
    }

    this.source.addEventListener('state', (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data)
        this.handler('state', data)
      } catch {
        // ignore
      }
    })

    this.source.addEventListener('action', (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data)
        this.handler('action', data)
      } catch {
        // ignore
      }
    })

    this.source.onerror = () => {
      // EventSource auto-reconnects; no manual handling needed
    }
  }

  disconnect() {
    if (this.source) {
      this.source.close()
      this.source = null
    }
  }
}
