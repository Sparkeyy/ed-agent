<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as api from '../api/client'
import type { PlayerProfile, PlayerClassification } from '../types'

const route = useRoute()
const router = useRouter()
const username = computed(() => route.params.username as string)

const profile = ref<PlayerProfile | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

const classificationIcons: Record<PlayerClassification, string> = {
  Seedling: '\u{1F331}',
  Wanderer: '\u{1F6B6}',
  Forager: '\u{1F344}',
  Ranger: '\u{1F3F9}',
  Elder: '\u{1F332}',
}

onMounted(async () => {
  await fetchProfile()
})

async function fetchProfile() {
  loading.value = true
  error.value = null
  try {
    profile.value = await api.getProfile(username.value)
  } catch (e: any) {
    error.value = e.message ?? 'Failed to load profile'
  } finally {
    loading.value = false
  }
}

// ELO sparkline: rendered as a simple CSS line chart
const sparklinePoints = computed(() => {
  if (!profile.value?.elo_history?.length) return ''
  const history = profile.value.elo_history
  const min = Math.min(...history)
  const max = Math.max(...history)
  const range = max - min || 1
  const width = 200
  const height = 40
  const step = history.length > 1 ? width / (history.length - 1) : width

  return history
    .map((elo, i) => {
      const x = i * step
      const y = height - ((elo - min) / range) * height
      return `${x},${y}`
    })
    .join(' ')
})

const sparklineViewBox = computed(() => {
  return `0 0 200 40`
})

function placementLabel(placement: number): string {
  if (placement === 1) return '1st'
  if (placement === 2) return '2nd'
  if (placement === 3) return '3rd'
  return `${placement}th`
}

function goToGame(gameId: string) {
  router.push(`/scores/${gameId}`)
}
</script>

<template>
  <div class="profile-view">
    <!-- Loading -->
    <div v-if="loading" class="profile-loading">
      <div class="loading-spinner"></div>
      <p>Loading profile...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="profile-error">
      <p class="error-text">{{ error }}</p>
      <button class="btn-retry" @click="fetchProfile">Retry</button>
    </div>

    <!-- Profile Content -->
    <div v-else-if="profile" class="profile-content">
      <!-- Header Card -->
      <div class="profile-header-card">
        <div class="profile-avatar">
          <span class="avatar-icon">{{ classificationIcons[profile.classification] }}</span>
        </div>
        <div class="profile-identity">
          <h1 class="profile-username">{{ profile.username }}</h1>
          <div class="profile-class-badge" :class="'class-' + profile.classification.toLowerCase()">
            {{ profile.classification }}
          </div>
        </div>
        <div class="profile-elo">
          <span class="elo-value">{{ profile.elo }}</span>
          <span class="elo-label">ELO</span>
        </div>
      </div>

      <!-- Stats Grid -->
      <div class="stats-grid">
        <div class="stat-card">
          <span class="stat-value">{{ profile.games_played }}</span>
          <span class="stat-label">Games Played</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ (profile.win_rate * 100).toFixed(1) }}%</span>
          <span class="stat-label">Win Rate</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ (profile.avg_move_accuracy * 100).toFixed(1) }}%</span>
          <span class="stat-label">Move Accuracy</span>
        </div>
      </div>

      <!-- ELO History -->
      <div class="elo-history" v-if="profile.elo_history && profile.elo_history.length > 1">
        <h2 class="section-title">Rating History</h2>
        <div class="sparkline-container">
          <svg :viewBox="sparklineViewBox" class="sparkline-svg" preserveAspectRatio="none">
            <polyline
              :points="sparklinePoints"
              fill="none"
              stroke="var(--forest-light)"
              stroke-width="2"
              stroke-linejoin="round"
              stroke-linecap="round"
            />
          </svg>
          <div class="sparkline-labels">
            <span class="sparkline-min">{{ Math.min(...profile.elo_history) }}</span>
            <span class="sparkline-max">{{ Math.max(...profile.elo_history) }}</span>
          </div>
        </div>
      </div>

      <!-- Game History -->
      <div class="game-history" v-if="profile.recent_games && profile.recent_games.length > 0">
        <h2 class="section-title">Recent Games</h2>
        <div class="history-list">
          <div
            v-for="game in profile.recent_games"
            :key="game.game_id"
            class="history-item"
            @click="goToGame(game.game_id)"
          >
            <div class="history-placement" :class="{ 'placement-win': game.placement === 1 }">
              {{ placementLabel(game.placement) }}
            </div>
            <div class="history-details">
              <div class="history-date">{{ game.date }}</div>
              <div class="history-players">{{ game.players }} players</div>
            </div>
            <div class="history-score">
              <span class="score-value">{{ game.score }}</span>
              <span class="score-label">pts</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profile-view {
  max-width: 640px;
  margin: 0 auto;
  animation: fadeIn 0.5s ease;
}

.profile-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--gap-xl) 0;
  gap: var(--gap-md);
  color: var(--ink-faint);
  font-family: var(--font-display);
}

.loading-spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--parchment-deep);
  border-top-color: var(--forest-light);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.profile-error {
  text-align: center;
  padding: var(--gap-xl) 0;
}

.error-text {
  color: var(--red-destination);
  margin-bottom: var(--gap-md);
}

.btn-retry {
  padding: 8px 24px;
  background: var(--forest-light);
  color: white;
  font-family: var(--font-display);
  font-size: 0.9rem;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 0.2s ease;
}

.btn-retry:hover {
  background: var(--forest-mid);
}

/* Header Card */
.profile-header-card {
  display: flex;
  align-items: center;
  gap: var(--gap-lg);
  background: white;
  border: var(--border-card);
  border-radius: var(--radius-lg);
  padding: var(--gap-lg) var(--gap-xl);
  box-shadow: var(--shadow-sm);
  margin-bottom: var(--gap-lg);
}

.profile-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--parchment-dark);
  border: 2px solid var(--parchment-deep);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.avatar-icon {
  font-size: 2rem;
}

.profile-identity {
  flex: 1;
}

.profile-username {
  font-family: var(--font-display);
  font-size: 1.6rem;
  color: var(--ink);
  margin-bottom: 4px;
}

.profile-class-badge {
  display: inline-block;
  padding: 2px 12px;
  border-radius: 12px;
  font-family: var(--font-display);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.class-seedling {
  background: #e8f0e4;
  color: #4a7c59;
}

.class-wanderer {
  background: var(--tan-traveler-bg);
  color: #8a6d00;
}

.class-forager {
  background: var(--blue-governance-bg);
  color: var(--blue-governance);
}

.class-ranger {
  background: var(--purple-prosperity-bg);
  color: var(--purple-prosperity);
}

.class-elder {
  background: linear-gradient(135deg, #fff8e0, #ffe8a0);
  color: #5a3e00;
  border: 1px solid var(--gold);
  box-shadow: 0 0 8px rgba(201, 169, 110, 0.3);
}

.profile-elo {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}

.elo-value {
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 700;
  color: var(--forest-dark);
}

.elo-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink-faint);
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--gap-md);
  margin-bottom: var(--gap-lg);
}

.stat-card {
  background: white;
  border: var(--border-card);
  border-radius: var(--radius-md);
  padding: var(--gap-md);
  text-align: center;
  box-shadow: var(--shadow-sm);
}

.stat-card .stat-value {
  display: block;
  font-family: var(--font-display);
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 2px;
}

.stat-card .stat-label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--ink-faint);
}

/* Section Title */
.section-title {
  font-family: var(--font-display);
  font-size: 1rem;
  color: var(--forest-mid);
  margin-bottom: var(--gap-md);
  padding-bottom: var(--gap-xs);
  border-bottom: 1px solid var(--parchment-deep);
}

/* ELO Sparkline */
.elo-history {
  margin-bottom: var(--gap-lg);
}

.sparkline-container {
  background: white;
  border: var(--border-card);
  border-radius: var(--radius-md);
  padding: var(--gap-md) var(--gap-lg);
  box-shadow: var(--shadow-sm);
}

.sparkline-svg {
  width: 100%;
  height: 48px;
  display: block;
}

.sparkline-labels {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-size: 0.7rem;
  color: var(--ink-faint);
}

/* Game History */
.game-history {
  margin-bottom: var(--gap-lg);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
}

.history-item {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
  padding: var(--gap-sm) var(--gap-md);
  background: white;
  border: var(--border-card);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 0.2s ease, box-shadow 0.2s ease;
}

.history-item:hover {
  background: var(--parchment-dark);
  box-shadow: var(--shadow-sm);
}

.history-placement {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--parchment-dark);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--ink-faint);
  flex-shrink: 0;
}

.history-placement.placement-win {
  background: linear-gradient(135deg, #ffd700, #ffb800);
  color: #5a3e00;
  box-shadow: 0 0 8px rgba(255, 215, 0, 0.3);
}

.history-details {
  flex: 1;
}

.history-date {
  font-size: 0.85rem;
  color: var(--ink);
}

.history-players {
  font-size: 0.75rem;
  color: var(--ink-faint);
}

.history-score {
  text-align: right;
  flex-shrink: 0;
}

.history-score .score-value {
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--ink);
}

.history-score .score-label {
  font-size: 0.7rem;
  color: var(--ink-faint);
  margin-left: 2px;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
