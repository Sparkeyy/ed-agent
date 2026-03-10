<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import * as api from '../api/client'
import type { LeaderboardEntry, PlayerClassification } from '../types'

const router = useRouter()
const entries = ref<LeaderboardEntry[]>([])
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
  await fetchLeaderboard()
})

async function fetchLeaderboard() {
  loading.value = true
  error.value = null
  try {
    entries.value = await api.getLeaderboard()
  } catch (e: any) {
    error.value = e.message ?? 'Failed to load leaderboard'
  } finally {
    loading.value = false
  }
}

function goToProfile(username: string) {
  router.push(`/profile/${encodeURIComponent(username)}`)
}

function rankDisplay(rank: number): string {
  if (rank === 1) return '\u{1F451}'
  if (rank === 2) return '\u{1F948}'
  if (rank === 3) return '\u{1F949}'
  return `#${rank}`
}
</script>

<template>
  <div class="leaderboard-view">
    <div class="leaderboard-hero">
      <h1 class="leaderboard-title">Leaderboard</h1>
      <p class="leaderboard-subtitle">The finest builders in Everdell Valley</p>
      <div class="divider">
        <span class="leaf">&#x1F33F;</span>
        <span class="divider-line"></span>
        <span class="leaf">&#x1F33F;</span>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="lb-loading">
      <div class="loading-spinner"></div>
      <p>Loading rankings...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="lb-error">
      <p class="error-text">{{ error }}</p>
      <button class="btn-retry" @click="fetchLeaderboard">Retry</button>
    </div>

    <!-- Leaderboard Table -->
    <div v-else-if="entries.length > 0" class="lb-table-wrapper">
      <table class="lb-table">
        <thead>
          <tr>
            <th class="col-rank">Rank</th>
            <th class="col-player">Player</th>
            <th class="col-elo">ELO</th>
            <th class="col-class">Class</th>
            <th class="col-games">Games</th>
            <th class="col-winrate">Win %</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="entry in entries"
            :key="entry.username"
            class="lb-row"
            :class="{ 'lb-top-3': entry.rank <= 3 }"
            @click="goToProfile(entry.username)"
          >
            <td class="col-rank">
              <span class="rank-badge" :class="'rank-' + entry.rank">
                {{ rankDisplay(entry.rank) }}
              </span>
            </td>
            <td class="col-player">
              <span class="player-name">{{ entry.username }}</span>
            </td>
            <td class="col-elo">
              <span class="elo-value">{{ entry.elo }}</span>
            </td>
            <td class="col-class">
              <span class="class-badge" :class="'class-' + entry.classification.toLowerCase()">
                {{ classificationIcons[entry.classification] }} {{ entry.classification }}
              </span>
            </td>
            <td class="col-games">{{ entry.games_played }}</td>
            <td class="col-winrate">{{ (entry.win_rate * 100).toFixed(1) }}%</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty State -->
    <div v-else class="lb-empty">
      <p>No players ranked yet. Start a game to appear on the leaderboard.</p>
    </div>
  </div>
</template>

<style scoped>
.leaderboard-view {
  max-width: 800px;
  margin: 0 auto;
  animation: fadeIn 0.5s ease;
}

.leaderboard-hero {
  text-align: center;
  margin-bottom: var(--gap-xl);
  padding-top: var(--gap-lg);
}

.leaderboard-title {
  font-family: var(--font-display);
  font-size: 2.2rem;
  color: var(--forest-dark);
  letter-spacing: 0.06em;
}

.leaderboard-subtitle {
  font-size: 1rem;
  color: var(--ink-faint);
  font-style: italic;
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

/* Loading / Error */
.lb-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
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

.lb-error {
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

/* Table */
.lb-table-wrapper {
  background: white;
  border: var(--border-card);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.lb-table {
  width: 100%;
  border-collapse: collapse;
}

.lb-table thead {
  background: var(--parchment-dark);
}

.lb-table th {
  font-family: var(--font-display);
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--ink-faint);
  padding: 10px 16px;
  text-align: left;
  border-bottom: 1px solid var(--parchment-deep);
}

.lb-table td {
  padding: 12px 16px;
  font-size: 0.9rem;
  color: var(--ink);
  border-bottom: 1px solid var(--parchment);
}

.lb-row {
  cursor: pointer;
  transition: background 0.15s ease;
}

.lb-row:hover {
  background: var(--parchment);
}

.lb-row:last-child td {
  border-bottom: none;
}

.lb-top-3 {
  background: rgba(201, 169, 110, 0.04);
}

.lb-top-3:hover {
  background: rgba(201, 169, 110, 0.1);
}

/* Rank */
.col-rank {
  width: 60px;
  text-align: center;
}

.rank-badge {
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 700;
}

.rank-1 {
  font-size: 1.3rem;
}

.rank-2 {
  font-size: 1.2rem;
}

.rank-3 {
  font-size: 1.1rem;
}

/* Player */
.player-name {
  font-weight: 600;
  color: var(--ink);
}

/* ELO */
.elo-value {
  font-family: var(--font-display);
  font-weight: 700;
  color: var(--forest-dark);
}

/* Classification */
.class-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 0.78rem;
  font-weight: 600;
  white-space: nowrap;
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
}

/* Games / Win rate */
.col-games, .col-winrate {
  text-align: right;
  width: 80px;
}

th.col-games, th.col-winrate {
  text-align: right;
}

/* Empty */
.lb-empty {
  text-align: center;
  padding: var(--gap-xl);
  color: var(--ink-faint);
  font-style: italic;
  background: white;
  border: var(--border-card);
  border-radius: var(--radius-lg);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
