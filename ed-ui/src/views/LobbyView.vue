<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'

const router = useRouter()
const store = useGameStore()

const playerName = ref('')
const numPlayers = ref(2)
const joinGameId = ref('')
const joinName = ref('')
const error = ref('')
const recentGames = ref<Array<{ gameId: string; date: string }>>([])

onMounted(() => {
  // Load recent games from localStorage
  const games: Array<{ gameId: string; date: string }> = []
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key && key.startsWith('everdell_session_')) {
      const gid = key.replace('everdell_session_', '')
      games.push({ gameId: gid, date: '' })
    }
  }
  recentGames.value = games.slice(0, 5)
})

async function handleCreate() {
  error.value = ''
  if (!playerName.value.trim()) {
    error.value = 'Enter your name to found a city'
    return
  }
  try {
    const gameId = await store.createNewGame(numPlayers.value, playerName.value)
    store.connectSSE()
    router.push(`/game/${gameId}`)
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function handleJoin() {
  error.value = ''
  if (!joinName.value.trim() || !joinGameId.value.trim()) {
    error.value = 'Enter your name and the game ID to join'
    return
  }
  try {
    await store.joinExistingGame(joinGameId.value, joinName.value)
    store.connectSSE()
    router.push(`/game/${joinGameId.value}`)
  } catch (e) {
    error.value = (e as Error).message
  }
}

function rejoinGame(gameId: string) {
  if (store.loadSession(gameId)) {
    store.connectSSE()
    router.push(`/game/${gameId}`)
  }
}
</script>

<template>
  <div class="lobby">
    <div class="lobby-hero">
      <h1 class="lobby-title">Everdell</h1>
      <p class="lobby-subtitle">Build a city of critters and constructions in the valley</p>
      <div class="divider">
        <span class="leaf">\u{1F33F}</span>
        <span class="divider-line"></span>
        <span class="leaf">\u{1F33F}</span>
      </div>
    </div>

    <div class="lobby-panels">
      <div class="panel">
        <h2 class="panel-title">Found a New City</h2>
        <div class="form-group">
          <label class="form-label">Your Name</label>
          <input
            v-model="playerName"
            type="text"
            class="form-input"
            placeholder="Enter your name..."
          />
        </div>
        <div class="form-group">
          <label class="form-label">Players</label>
          <select v-model="numPlayers" class="form-input">
            <option :value="2">2 Players</option>
            <option :value="3">3 Players</option>
            <option :value="4">4 Players</option>
          </select>
        </div>
        <button class="btn btn-primary" @click="handleCreate" :disabled="store.loading">
          <span v-if="store.loading">Creating...</span>
          <span v-else>Found a New City</span>
        </button>
      </div>

      <div class="panel">
        <h2 class="panel-title">Join the Valley</h2>
        <div class="form-group">
          <label class="form-label">Game ID</label>
          <input
            v-model="joinGameId"
            type="text"
            class="form-input"
            placeholder="Enter game ID..."
          />
        </div>
        <div class="form-group">
          <label class="form-label">Your Name</label>
          <input
            v-model="joinName"
            type="text"
            class="form-input"
            placeholder="Enter your name..."
          />
        </div>
        <button class="btn btn-secondary" @click="handleJoin" :disabled="store.loading">
          <span v-if="store.loading">Joining...</span>
          <span v-else>Join the Valley</span>
        </button>
      </div>
    </div>

    <div v-if="recentGames.length > 0" class="recent-section">
      <h3 class="recent-title">Recent Games</h3>
      <div class="recent-list">
        <button
          v-for="game in recentGames"
          :key="game.gameId"
          class="recent-item"
          @click="rejoinGame(game.gameId)"
        >
          <span class="recent-id">{{ game.gameId.slice(0, 8) }}...</span>
          <span class="recent-action">Rejoin \u2192</span>
        </button>
      </div>
    </div>

    <p v-if="error" class="error-msg">{{ error }}</p>
  </div>
</template>

<style scoped>
.lobby {
  max-width: 600px;
  margin: 0 auto;
  animation: fadeIn 0.5s ease;
}

.lobby-hero {
  text-align: center;
  margin-bottom: var(--gap-xl);
  padding-top: var(--gap-lg);
}

.lobby-title {
  font-family: var(--font-display);
  font-size: 3rem;
  color: var(--forest-dark);
  letter-spacing: 0.08em;
  margin-bottom: var(--gap-xs);
}

.lobby-subtitle {
  font-family: var(--font-body);
  font-size: 1.05rem;
  color: var(--ink-faint);
  font-style: italic;
}

.divider {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--gap-sm);
  margin-top: var(--gap-md);
}

.divider-line {
  width: 80px;
  height: 1px;
  background: var(--parchment-deep);
}

.leaf {
  opacity: 0.6;
  font-size: 0.9rem;
}

.lobby-panels {
  display: flex;
  flex-direction: column;
  gap: var(--gap-lg);
}

.panel {
  background: white;
  border: var(--border-card);
  border-radius: var(--radius-lg);
  padding: var(--gap-lg);
  box-shadow: var(--shadow-sm);
}

.panel-title {
  font-family: var(--font-display);
  font-size: 1.2rem;
  color: var(--forest-mid);
  margin-bottom: var(--gap-md);
}

.form-group {
  margin-bottom: var(--gap-md);
}

.form-label {
  display: block;
  font-size: 0.82rem;
  color: var(--ink-light);
  font-weight: 600;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.form-input {
  display: block;
  width: 100%;
  padding: 10px 14px;
  border: 1.5px solid var(--parchment-deep);
  border-radius: var(--radius-md);
  background: var(--parchment);
  font-size: 1rem;
  color: var(--ink);
  transition: border-color 0.2s ease;
}

.form-input:focus {
  outline: none;
  border-color: var(--gold);
  box-shadow: 0 0 0 3px rgba(201, 169, 110, 0.15);
}

.btn {
  display: block;
  width: 100%;
  padding: 12px;
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 0.2s ease, transform 0.15s ease;
}

.btn:active {
  transform: scale(0.98);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--forest-light);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--forest-mid);
}

.btn-secondary {
  background: var(--gold);
  color: var(--ink);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--gold-bright);
}

.recent-section {
  margin-top: var(--gap-xl);
}

.recent-title {
  font-family: var(--font-display);
  font-size: 0.95rem;
  color: var(--ink-faint);
  margin-bottom: var(--gap-sm);
}

.recent-list {
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
}

.recent-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--gap-sm) var(--gap-md);
  background: white;
  border: var(--border-card);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 0.2s ease;
}

.recent-item:hover {
  background: var(--parchment-dark);
}

.recent-id {
  font-family: monospace;
  font-size: 0.85rem;
  color: var(--ink-light);
}

.recent-action {
  font-size: 0.82rem;
  color: var(--forest-light);
  font-weight: 600;
}

.error-msg {
  margin-top: var(--gap-md);
  padding: var(--gap-sm) var(--gap-md);
  background: var(--red-destination-bg);
  color: var(--red-destination);
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  text-align: center;
}
</style>
