<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { createGame, joinGame } from '../api/client'
import { useGameStore } from '../stores/game'

const router = useRouter()
const store = useGameStore()

const playerName = ref('')
const numPlayers = ref(2)
const joinGameId = ref('')
const error = ref('')

async function handleCreate() {
  error.value = ''
  if (!playerName.value.trim()) {
    error.value = 'Enter your name'
    return
  }
  try {
    const { gameId } = await createGame({
      playerName: playerName.value,
      numPlayers: numPlayers.value,
    })
    const { playerId } = await joinGame(gameId, { playerName: playerName.value })
    store.myPlayerId = playerId
    router.push(`/game/${gameId}`)
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function handleJoin() {
  error.value = ''
  if (!playerName.value.trim() || !joinGameId.value.trim()) {
    error.value = 'Enter your name and game ID'
    return
  }
  try {
    const { playerId } = await joinGame(joinGameId.value, { playerName: playerName.value })
    store.myPlayerId = playerId
    router.push(`/game/${joinGameId.value}`)
  } catch (e) {
    error.value = (e as Error).message
  }
}
</script>

<template>
  <div class="lobby">
    <h2>Welcome to Everdell</h2>

    <div class="form-section">
      <label>
        Your Name
        <input v-model="playerName" type="text" placeholder="Enter your name" />
      </label>
    </div>

    <div class="form-section">
      <h3>Create New Game</h3>
      <label>
        Number of Players
        <select v-model="numPlayers">
          <option :value="2">2 Players</option>
          <option :value="3">3 Players</option>
          <option :value="4">4 Players</option>
        </select>
      </label>
      <button @click="handleCreate">Create Game</button>
    </div>

    <div class="form-section">
      <h3>Join Existing Game</h3>
      <label>
        Game ID
        <input v-model="joinGameId" type="text" placeholder="Enter game ID" />
      </label>
      <button @click="handleJoin">Join Game</button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<style scoped>
.lobby {
  max-width: 500px;
  margin: 2rem auto;
}

h2 {
  margin-bottom: 1.5rem;
}

.form-section {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: white;
  border-radius: 8px;
}

.form-section h3 {
  margin-bottom: 0.75rem;
}

label {
  display: block;
  margin-bottom: 0.5rem;
}

input, select {
  display: block;
  width: 100%;
  padding: 0.5rem;
  margin-top: 0.25rem;
  border: 1px solid #ccc;
  border-radius: 4px;
}

button {
  margin-top: 0.75rem;
  padding: 0.5rem 1.5rem;
  background: #3a5a40;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:hover {
  background: #2d4a33;
}

.error {
  color: #c0392b;
  margin-top: 1rem;
}
</style>
