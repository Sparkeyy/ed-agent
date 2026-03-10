<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'

interface DifficultyStats {
  games: number
  completed: number
  avg_winner_vp: number
  avg_vp: number
  min_vp: number
  max_vp: number
  vp_over_time: number[]
  top_cards: [string, number][]
  avg_breakdown: Record<string, number>
}

interface MixedDiffStats {
  avg_vp: number
  win_rate: number
  wins: number
  appearances: number
  min_vp: number
  max_vp: number
}

interface MixedData {
  games: number
  completed: number
  by_difficulty: Record<string, MixedDiffStats>
}

interface TrainingSummary {
  generated_at: string
  by_player_count: Record<string, Record<string, DifficultyStats>>
  mixed?: Record<string, MixedData>
}

const summary = ref<TrainingSummary | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const selectedPlayers = ref('2')

const DIFFICULTIES = ['apprentice', 'journeyman', 'master'] as const
const DIFF_COLORS: Record<string, string> = {
  apprentice: '#c0392b',
  journeyman: '#d4a017',
  master: '#27ae60',
}
const DIFF_LABELS: Record<string, string> = {
  apprentice: 'Apprentice',
  journeyman: 'Journeyman',
  master: 'Master',
}

onMounted(async () => {
  try {
    const resp = await fetch('/data/training_summary.json')
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    summary.value = await resp.json()
  } catch (e: any) {
    error.value = e.message ?? 'Failed to load training data'
  } finally {
    loading.value = false
  }
})

const currentData = computed(() => {
  if (!summary.value) return null
  return summary.value.by_player_count[selectedPlayers.value] ?? null
})

const availablePlayers = computed(() => {
  if (!summary.value) return []
  return Object.keys(summary.value.by_player_count).sort()
})

// SVG chart dimensions
const chartW = 800
const chartH = 300
const padL = 50
const padR = 20
const padT = 20
const padB = 40
const plotW = chartW - padL - padR
const plotH = chartH - padT - padB

function buildLinePath(data: number[]): string {
  if (!data.length) return ''
  const xStep = plotW / Math.max(data.length - 1, 1)

  // Find global min/max across all difficulties for consistent Y scale
  const allVP: number[] = []
  if (currentData.value) {
    for (const diff of DIFFICULTIES) {
      const stats = currentData.value[diff]
      if (stats?.vp_over_time) {
        allVP.push(...stats.vp_over_time)
      }
    }
  }
  const minVP = allVP.length ? Math.min(...allVP) : 0
  const maxVP = allVP.length ? Math.max(...allVP) : 100
  const range = maxVP - minVP || 1

  return data
    .map((vp, i) => {
      const x = padL + i * xStep
      const y = padT + plotH - ((vp - minVP) / range) * plotH
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
}

const yAxisLabels = computed(() => {
  if (!currentData.value) return []
  const allVP: number[] = []
  for (const diff of DIFFICULTIES) {
    const stats = currentData.value[diff]
    if (stats?.vp_over_time) allVP.push(...stats.vp_over_time)
  }
  if (!allVP.length) return []

  const minVP = Math.min(...allVP)
  const maxVP = Math.max(...allVP)
  const range = maxVP - minVP || 1
  const step = Math.ceil(range / 5)
  const start = Math.floor(minVP / step) * step

  const labels = []
  for (let v = start; v <= maxVP + step; v += step) {
    const y = padT + plotH - ((v - minVP) / range) * plotH
    if (y >= padT && y <= padT + plotH) {
      labels.push({ value: v, y })
    }
  }
  return labels
})

const xAxisLabels = computed(() => {
  if (!currentData.value) return []
  // Use first available difficulty to get data length
  for (const diff of DIFFICULTIES) {
    const stats = currentData.value[diff]
    if (stats?.vp_over_time?.length) {
      const len = stats.vp_over_time.length
      const totalGames = stats.games
      const labels = []
      const numLabels = 5
      for (let i = 0; i <= numLabels; i++) {
        const idx = Math.round((i / numLabels) * (len - 1))
        const x = padL + (idx / Math.max(len - 1, 1)) * plotW
        const gameNum = Math.round((idx / Math.max(len - 1, 1)) * totalGames)
        labels.push({ x, label: gameNum >= 1000 ? `${(gameNum / 1000).toFixed(0)}K` : String(gameNum) })
      }
      return labels
    }
  }
  return []
})

// Top cards: merge across difficulties, show best from master
const topCards = computed(() => {
  if (!currentData.value) return []
  const masterStats = currentData.value['master']
  if (!masterStats?.top_cards) return []
  return masterStats.top_cards.slice(0, 10)
})

// Mixed-difficulty data for selected player count
const mixedData = computed(() => {
  if (!summary.value?.mixed) return null
  return summary.value.mixed[selectedPlayers.value] ?? null
})
</script>

<template>
  <div class="training-view">
    <h1 class="page-title">AI Training Results</h1>

    <!-- Loading -->
    <div v-if="loading" class="training-loading">
      <div class="loading-spinner"></div>
      <p>Loading training data...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="training-error">
      <p class="error-text">{{ error }}</p>
      <p class="error-hint">Run <code>python3 tools/simulate.py --difficulty all</code> to generate data.</p>
    </div>

    <!-- Content -->
    <div v-else-if="summary && currentData" class="training-content">
      <!-- Generated timestamp -->
      <p class="generated-at">Data from {{ new Date(summary.generated_at).toLocaleDateString() }}</p>

      <!-- Player count tabs -->
      <div class="tab-bar">
        <button
          v-for="pc in availablePlayers"
          :key="pc"
          :class="['tab', { active: selectedPlayers === pc }]"
          @click="selectedPlayers = pc"
        >
          {{ pc }} Players
        </button>
      </div>

      <!-- VP Over Time Chart -->
      <div class="chart-section">
        <h2 class="section-title">Winner VP Over Time (rolling avg, 100-game windows)</h2>
        <div class="chart-container">
          <svg :viewBox="`0 0 ${chartW} ${chartH}`" class="vp-chart" preserveAspectRatio="xMidYMid meet">
            <!-- Grid lines -->
            <line
              v-for="label in yAxisLabels"
              :key="'grid-' + label.value"
              :x1="padL" :y1="label.y"
              :x2="chartW - padR" :y2="label.y"
              stroke="#e0ddd5" stroke-width="1"
            />

            <!-- Y axis labels -->
            <text
              v-for="label in yAxisLabels"
              :key="'ylabel-' + label.value"
              :x="padL - 8" :y="label.y + 4"
              text-anchor="end" font-size="12" fill="#7a7568"
            >{{ label.value }}</text>

            <!-- X axis labels -->
            <text
              v-for="label in xAxisLabels"
              :key="'xlabel-' + label.label"
              :x="label.x" :y="chartH - 8"
              text-anchor="middle" font-size="12" fill="#7a7568"
            >{{ label.label }}</text>

            <!-- X axis title -->
            <text :x="padL + plotW / 2" :y="chartH" text-anchor="middle" font-size="13" fill="#7a7568">
              Games Played
            </text>

            <!-- Data lines -->
            <template v-for="diff in DIFFICULTIES" :key="diff">
              <path
                v-if="currentData[diff]?.vp_over_time"
                :d="buildLinePath(currentData[diff].vp_over_time)"
                fill="none"
                :stroke="DIFF_COLORS[diff]"
                stroke-width="2.5"
                stroke-linejoin="round"
                stroke-linecap="round"
              >
                <title>{{ DIFF_LABELS[diff] }}</title>
              </path>
            </template>
          </svg>

          <!-- Legend -->
          <div class="chart-legend">
            <span v-for="diff in DIFFICULTIES" :key="diff" class="legend-item">
              <span class="legend-swatch" :style="{ background: DIFF_COLORS[diff] }"></span>
              {{ DIFF_LABELS[diff] }}
            </span>
          </div>
        </div>
      </div>

      <!-- Expected VP by Difficulty -->
      <div class="stats-section">
        <h2 class="section-title">Expected VP by Difficulty</h2>
        <div class="difficulty-cards">
          <template v-for="diff in DIFFICULTIES" :key="diff">
          <div
            v-if="currentData[diff]"
            class="diff-card"
            :class="'diff-' + diff"
          >
            <div class="diff-name">{{ DIFF_LABELS[diff] }}</div>
            <div class="diff-vp">~{{ currentData[diff].avg_vp }} VP</div>
            <div class="diff-detail">
              Winner avg: {{ currentData[diff].avg_winner_vp }}
            </div>
            <div class="diff-detail">
              Range: {{ currentData[diff].min_vp }}&ndash;{{ currentData[diff].max_vp }}
            </div>
            <div class="diff-detail">
              {{ currentData[diff].completed.toLocaleString() }} / {{ currentData[diff].games.toLocaleString() }} completed
            </div>
          </div>
          </template>
        </div>
      </div>

      <!-- Score Breakdown -->
      <div class="breakdown-section" v-if="currentData['master']?.avg_breakdown">
        <h2 class="section-title">Average Score Breakdown (Master)</h2>
        <div class="breakdown-bars">
          <div
            v-for="(val, key) in currentData['master'].avg_breakdown"
            :key="key"
            class="breakdown-row"
          >
            <span class="breakdown-label">{{ String(key).replace(/_/g, ' ') }}</span>
            <div class="breakdown-bar-track">
              <div
                class="breakdown-bar-fill"
                :style="{ width: Math.min(100, (val / (currentData['master'].avg_vp || 1)) * 100) + '%' }"
              ></div>
            </div>
            <span class="breakdown-value">{{ val.toFixed(1) }}</span>
          </div>
        </div>
      </div>

      <!-- Top Cards -->
      <div class="cards-section" v-if="topCards.length">
        <h2 class="section-title">Top Cards by Win Rate (Master)</h2>
        <div class="card-bars">
          <div v-for="[card, rate] in topCards" :key="card" class="card-row">
            <span class="card-name">{{ card }}</span>
            <div class="card-bar-track">
              <div class="card-bar-fill" :style="{ width: (rate * 100) + '%' }"></div>
            </div>
            <span class="card-rate">{{ (rate * 100).toFixed(0) }}%</span>
          </div>
        </div>
      </div>

      <!-- Mixed Difficulty Results -->
      <div class="mixed-section" v-if="mixedData">
        <h2 class="section-title">Mixed Difficulty Games ({{ mixedData.games.toLocaleString() }} games)</h2>
        <p class="mixed-subtitle">Each player randomly assigned a difficulty. Shows relative strength when different AI levels compete head-to-head.</p>

        <div class="mixed-cards">
          <template v-for="diff in DIFFICULTIES" :key="'mixed-' + diff">
          <div
            v-if="mixedData.by_difficulty[diff]"
            class="mixed-card"
            :class="'diff-' + diff"
          >
            <div class="diff-name">{{ DIFF_LABELS[diff] }}</div>
            <div class="mixed-win-rate">{{ (mixedData.by_difficulty[diff].win_rate * 100).toFixed(1) }}%</div>
            <div class="mixed-win-label">win rate</div>
            <div class="mixed-stats">
              <div class="mixed-stat">
                <span class="mixed-stat-value">{{ mixedData.by_difficulty[diff].avg_vp }}</span>
                <span class="mixed-stat-label">avg VP</span>
              </div>
              <div class="mixed-stat">
                <span class="mixed-stat-value">{{ mixedData.by_difficulty[diff].wins.toLocaleString() }}</span>
                <span class="mixed-stat-label">wins</span>
              </div>
              <div class="mixed-stat">
                <span class="mixed-stat-value">{{ mixedData.by_difficulty[diff].min_vp }}&ndash;{{ mixedData.by_difficulty[diff].max_vp }}</span>
                <span class="mixed-stat-label">VP range</span>
              </div>
            </div>
          </div>
          </template>
        </div>

        <!-- Win rate bar visualization -->
        <div class="mixed-bar-container" v-if="mixedData.by_difficulty">
          <div class="mixed-bar">
            <template v-for="diff in DIFFICULTIES" :key="'bar-' + diff">
            <div
              v-if="mixedData.by_difficulty[diff]"
              class="mixed-bar-segment"
              :class="'bg-' + diff"
              :style="{ width: (mixedData.by_difficulty[diff].win_rate * 100) + '%' }"
            >
              <span v-if="mixedData.by_difficulty[diff].win_rate > 0.08" class="bar-label">
                {{ DIFF_LABELS[diff] }} {{ (mixedData.by_difficulty[diff].win_rate * 100).toFixed(0) }}%
              </span>
            </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.training-view {
  max-width: 900px;
  margin: 0 auto;
  animation: fadeIn 0.5s ease;
}

.page-title {
  font-family: var(--font-display);
  font-size: 1.8rem;
  color: var(--ink);
  margin-bottom: var(--gap-sm);
}

.generated-at {
  font-size: 0.8rem;
  color: var(--ink-faint);
  margin-bottom: var(--gap-lg);
}

.training-loading {
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

.training-error {
  text-align: center;
  padding: var(--gap-xl) 0;
}

.error-text {
  color: var(--red-destination);
  margin-bottom: var(--gap-sm);
}

.error-hint {
  color: var(--ink-faint);
  font-size: 0.85rem;
}

.error-hint code {
  background: var(--parchment-dark);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.8rem;
}

/* Tab bar */
.tab-bar {
  display: flex;
  gap: var(--gap-xs);
  margin-bottom: var(--gap-lg);
}

.tab {
  padding: 8px 20px;
  background: white;
  border: var(--border-card);
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.2s ease;
  color: var(--ink-faint);
}

.tab:hover {
  background: var(--parchment-dark);
}

.tab.active {
  background: var(--forest-dark);
  color: var(--gold-bright);
  border-color: var(--forest-dark);
}

/* Chart */
.chart-section, .stats-section, .cards-section, .breakdown-section {
  margin-bottom: var(--gap-xl);
}

.section-title {
  font-family: var(--font-display);
  font-size: 1rem;
  color: var(--forest-mid);
  margin-bottom: var(--gap-md);
  padding-bottom: var(--gap-xs);
  border-bottom: 1px solid var(--parchment-deep);
}

.chart-container {
  background: white;
  border: var(--border-card);
  border-radius: var(--radius-lg);
  padding: var(--gap-md);
  box-shadow: var(--shadow-sm);
}

.vp-chart {
  width: 100%;
  height: auto;
  display: block;
}

.chart-legend {
  display: flex;
  justify-content: center;
  gap: var(--gap-lg);
  margin-top: var(--gap-sm);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.82rem;
  color: var(--ink);
}

.legend-swatch {
  width: 14px;
  height: 3px;
  border-radius: 2px;
}

/* Difficulty cards */
.difficulty-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--gap-md);
}

.diff-card {
  background: white;
  border: var(--border-card);
  border-radius: var(--radius-md);
  padding: var(--gap-md) var(--gap-lg);
  text-align: center;
  box-shadow: var(--shadow-sm);
  border-top: 3px solid transparent;
}

.diff-apprentice { border-top-color: #c0392b; }
.diff-journeyman { border-top-color: #d4a017; }
.diff-master { border-top-color: #27ae60; }

.diff-name {
  font-family: var(--font-display);
  font-size: 0.9rem;
  color: var(--ink-faint);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.diff-vp {
  font-family: var(--font-display);
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 8px;
}

.diff-detail {
  font-size: 0.78rem;
  color: var(--ink-faint);
  line-height: 1.6;
}

/* Score breakdown bars */
.breakdown-bars {
  background: white;
  border: var(--border-card);
  border-radius: var(--radius-md);
  padding: var(--gap-md);
  box-shadow: var(--shadow-sm);
}

.breakdown-row {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
  padding: 4px 0;
}

.breakdown-label {
  width: 140px;
  font-size: 0.82rem;
  color: var(--ink);
  text-transform: capitalize;
  flex-shrink: 0;
}

.breakdown-bar-track {
  flex: 1;
  height: 12px;
  background: var(--parchment-dark);
  border-radius: 6px;
  overflow: hidden;
}

.breakdown-bar-fill {
  height: 100%;
  background: var(--forest-light);
  border-radius: 6px;
  transition: width 0.5s ease;
}

.breakdown-value {
  width: 40px;
  text-align: right;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--ink);
  flex-shrink: 0;
}

/* Top cards bars */
.card-bars {
  background: white;
  border: var(--border-card);
  border-radius: var(--radius-md);
  padding: var(--gap-md);
  box-shadow: var(--shadow-sm);
}

.card-row {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
  padding: 4px 0;
}

.card-name {
  width: 140px;
  font-size: 0.82rem;
  color: var(--ink);
  flex-shrink: 0;
}

.card-bar-track {
  flex: 1;
  height: 16px;
  background: var(--parchment-dark);
  border-radius: 8px;
  overflow: hidden;
}

.card-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--forest-light), var(--forest-mid));
  border-radius: 8px;
  transition: width 0.5s ease;
}

.card-rate {
  width: 40px;
  text-align: right;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--ink);
  flex-shrink: 0;
}

/* Mixed difficulty section */
.mixed-section {
  margin-bottom: var(--gap-xl);
}

.mixed-subtitle {
  font-size: 0.82rem;
  color: var(--ink-faint);
  margin-bottom: var(--gap-md);
  font-style: italic;
}

.mixed-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--gap-md);
  margin-bottom: var(--gap-lg);
}

.mixed-card {
  background: white;
  border: var(--border-card);
  border-radius: var(--radius-md);
  padding: var(--gap-md) var(--gap-lg);
  text-align: center;
  box-shadow: var(--shadow-sm);
  border-top: 3px solid transparent;
}

.mixed-win-rate {
  font-family: var(--font-display);
  font-size: 2.2rem;
  font-weight: 700;
  color: var(--ink);
  line-height: 1.1;
}

.mixed-win-label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--ink-faint);
  margin-bottom: 8px;
}

.mixed-stats {
  display: flex;
  justify-content: center;
  gap: var(--gap-md);
  border-top: 1px solid var(--parchment-deep);
  padding-top: 8px;
}

.mixed-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.mixed-stat-value {
  font-family: var(--font-display);
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--ink);
}

.mixed-stat-label {
  font-size: 0.65rem;
  color: var(--ink-faint);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.mixed-bar-container {
  background: white;
  border: var(--border-card);
  border-radius: var(--radius-md);
  padding: var(--gap-md);
  box-shadow: var(--shadow-sm);
}

.mixed-bar {
  display: flex;
  height: 36px;
  border-radius: 8px;
  overflow: hidden;
}

.mixed-bar-segment {
  display: flex;
  align-items: center;
  justify-content: center;
  transition: width 0.5s ease;
}

.bar-label {
  font-size: 0.72rem;
  font-weight: 600;
  color: white;
  white-space: nowrap;
  text-shadow: 0 1px 2px rgba(0,0,0,0.3);
}

.bg-apprentice { background: #c0392b; }
.bg-journeyman { background: #d4a017; }
.bg-master { background: #27ae60; }

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 600px) {
  .difficulty-cards {
    grid-template-columns: 1fr;
  }
  .card-name, .breakdown-label {
    width: 100px;
  }
}
</style>
