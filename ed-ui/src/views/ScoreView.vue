<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import type { PlayerData } from '../types'
import ResourceDisplay from '../components/ResourceDisplay.vue'

const route = useRoute()
const router = useRouter()
const store = useGameStore()
const gameId = route.params.id as string

onMounted(() => {
  if (!store.gameId) {
    store.loadSession(gameId)
  }
  if (!store.state) {
    store.connectSSE()
    store.refreshState()
  }
})

const sortedPlayers = computed<PlayerData[]>(() => {
  if (!store.state?.players) return []
  return [...store.state.players].sort((a, b) => b.score - a.score)
})

const winnerId = computed(() => {
  return sortedPlayers.value.length > 0 ? sortedPlayers.value[0].id : null
})

function cardBasePoints(player: PlayerData): number {
  return player.city.reduce((sum, card) => sum + card.base_points, 0)
}

function goToLobby() {
  store.disconnect()
  router.push('/')
}
</script>

<template>
  <div class="score-view">
    <div class="score-hero">
      <h1 class="score-title">Final Scores</h1>
      <p class="score-subtitle">Game {{ gameId.slice(0, 8) }}</p>
      <div class="divider">
        <span class="leaf">\u{1F33F}</span>
        <span class="divider-line"></span>
        <span class="leaf">\u{1F33F}</span>
      </div>
    </div>

    <div class="score-cards">
      <div
        v-for="(player, index) in sortedPlayers"
        :key="player.id"
        class="score-card"
        :class="{ winner: player.id === winnerId }"
      >
        <div class="score-rank">
          <span v-if="index === 0" class="crown">\u{1F451}</span>
          <span v-else class="rank-number">#{{ index + 1 }}</span>
        </div>
        <div class="score-player-info">
          <h2 class="score-player-name">{{ player.name }}</h2>
          <div class="score-total">\u2B50 {{ player.score }} points</div>
        </div>
        <div class="score-breakdown">
          <div class="breakdown-row">
            <span class="breakdown-label">Base Card Points</span>
            <span class="breakdown-value">{{ cardBasePoints(player) }}</span>
          </div>
          <div class="breakdown-row">
            <span class="breakdown-label">City Cards</span>
            <span class="breakdown-value">{{ player.city.length }}</span>
          </div>
          <div class="breakdown-row">
            <span class="breakdown-label">Season</span>
            <span class="breakdown-value">{{ player.season }}</span>
          </div>
          <div class="breakdown-row">
            <span class="breakdown-label">Total Score</span>
            <span class="breakdown-value total">{{ player.score }}</span>
          </div>
        </div>
        <div class="score-resources">
          <ResourceDisplay :resources="player.resources" :compact="true" />
        </div>
      </div>
    </div>

    <button class="btn-lobby" @click="goToLobby">Return to Lobby</button>
  </div>
</template>

<style scoped>
.score-view {
  max-width: 700px;
  margin: 0 auto;
  animation: fadeIn 0.6s ease;
}

.score-hero {
  text-align: center;
  margin-bottom: var(--gap-xl);
  padding-top: var(--gap-lg);
}

.score-title {
  font-family: var(--font-display);
  font-size: 2.2rem;
  color: var(--forest-dark);
  letter-spacing: 0.06em;
}

.score-subtitle {
  font-size: 0.9rem;
  color: var(--ink-faint);
  font-family: monospace;
  margin-top: var(--gap-xs);
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

.score-cards {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
}

.score-card {
  background: white;
  border: var(--border-card);
  border-radius: var(--radius-lg);
  padding: var(--gap-lg);
  box-shadow: var(--shadow-sm);
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-rows: auto auto auto;
  gap: var(--gap-sm) var(--gap-md);
  transition: box-shadow 0.3s ease;
}

.score-card.winner {
  border: var(--border-accent);
  box-shadow: var(--shadow-glow);
  background: linear-gradient(135deg, #fffdf8, rgba(201, 169, 110, 0.08));
}

.score-rank {
  grid-row: 1 / 3;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 50px;
}

.crown {
  font-size: 2rem;
}

.rank-number {
  font-family: var(--font-display);
  font-size: 1.4rem;
  color: var(--ink-faint);
}

.score-player-name {
  font-family: var(--font-display);
  font-size: 1.3rem;
  color: var(--ink);
}

.score-total {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--forest-light);
  margin-top: 2px;
}

.score-breakdown {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--gap-xs) var(--gap-md);
  padding-top: var(--gap-sm);
  border-top: 1px solid var(--parchment-deep);
}

.breakdown-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.breakdown-label {
  font-size: 0.8rem;
  color: var(--ink-faint);
}

.breakdown-value {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--ink);
}

.breakdown-value.total {
  font-size: 1.1rem;
  color: var(--forest-light);
}

.score-resources {
  grid-column: 1 / -1;
  padding-top: var(--gap-xs);
}

.btn-lobby {
  display: block;
  width: 100%;
  max-width: 300px;
  margin: var(--gap-xl) auto 0;
  padding: 12px;
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  background: var(--forest-light);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 0.2s ease;
}

.btn-lobby:hover {
  background: var(--forest-mid);
}
</style>
