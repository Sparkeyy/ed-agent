<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useGameStore } from '../stores/game'
import type { PlayerData, ResourceBank } from '../types'
import { RESOURCE_ICONS } from '../types'

const store = useGameStore()
const visible = ref(false)

function toggle() {
  visible.value = !visible.value
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Tab' && !e.ctrlKey && !e.metaKey && !e.altKey) {
    const tag = (e.target as HTMLElement)?.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
    e.preventDefault()
    toggle()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

// Derive stats from game state
const players = computed<PlayerData[]>(() => store.state?.players ?? [])

// Resource totals (in city cards cost = spent, current resources = gathered remainder)
function totalResources(player: PlayerData): number {
  const r = player.resources
  return r.twig + r.resin + r.pebble + r.berry
}

function resourcesSpent(player: PlayerData): ResourceBank {
  const spent = { twig: 0, resin: 0, pebble: 0, berry: 0 }
  for (const card of player.city) {
    spent.twig += card.cost.twig
    spent.resin += card.cost.resin
    spent.pebble += card.cost.pebble
    spent.berry += card.cost.berry
  }
  return spent
}

function totalSpent(player: PlayerData): number {
  const s = resourcesSpent(player)
  return s.twig + s.resin + s.pebble + s.berry
}

// Worker utilization
function workerUtilization(player: PlayerData): number {
  if (player.workers_total === 0) return 0
  return Math.round((player.workers_placed / player.workers_total) * 100)
}

// Max resource bar value for consistent scaling
const maxResourceValue = computed(() => {
  let max = 1
  for (const p of players.value) {
    const spent = totalSpent(p)
    const current = totalResources(p)
    max = Math.max(max, spent, current)
  }
  return max
})

const maxPoints = computed(() => {
  let max = 1
  for (const p of players.value) {
    max = Math.max(max, p.score)
  }
  return max
})

// Player colors for bars
const playerColors = ['var(--forest-light)', 'var(--gold)', 'var(--blue-governance)', 'var(--purple-prosperity)']

defineExpose({ toggle })
</script>

<template>
  <div class="stats-toggle-btn" @click="toggle" title="Statistics (Tab)">
    <span class="stats-icon">&#x1F4CA;</span>
  </div>

  <Transition name="slide-left">
    <div v-if="visible" class="stats-panel">
      <div class="stats-header">
        <h3 class="stats-title">Game Statistics</h3>
        <button class="stats-close" @click="toggle">&times;</button>
      </div>

      <div class="stats-body" v-if="store.state">
        <!-- Point Estimates -->
        <section class="stats-section">
          <h4 class="section-heading">Estimated Points</h4>
          <div class="bar-chart">
            <div
              v-for="(player, i) in players"
              :key="player.id + '-pts'"
              class="bar-row"
            >
              <span class="bar-label">{{ player.name }}</span>
              <div class="bar-track">
                <div
                  class="bar-fill"
                  :style="{
                    width: maxPoints > 0 ? (player.score / maxPoints * 100) + '%' : '0%',
                    background: playerColors[i % playerColors.length],
                  }"
                ></div>
              </div>
              <span class="bar-value">{{ player.score }}</span>
            </div>
          </div>
        </section>

        <!-- Economy: Resources Spent -->
        <section class="stats-section">
          <h4 class="section-heading">Resources Spent</h4>
          <div class="bar-chart">
            <div
              v-for="(player, i) in players"
              :key="player.id + '-spent'"
              class="bar-row"
            >
              <span class="bar-label">{{ player.name }}</span>
              <div class="bar-track">
                <div
                  class="bar-fill"
                  :style="{
                    width: maxResourceValue > 0 ? (totalSpent(player) / maxResourceValue * 100) + '%' : '0%',
                    background: playerColors[i % playerColors.length],
                  }"
                ></div>
              </div>
              <span class="bar-value">{{ totalSpent(player) }}</span>
            </div>
          </div>
        </section>

        <!-- Resources On Hand -->
        <section class="stats-section">
          <h4 class="section-heading">Resources On Hand</h4>
          <div class="resource-grid">
            <div
              v-for="(player, i) in players"
              :key="player.id + '-res'"
              class="resource-row"
            >
              <span class="res-player" :style="{ color: playerColors[i % playerColors.length] }">
                {{ player.name }}
              </span>
              <div class="res-items">
                <span class="res-item" v-for="(icon, key) in RESOURCE_ICONS" :key="key">
                  {{ icon }} {{ player.resources[key as keyof ResourceBank] }}
                </span>
              </div>
            </div>
          </div>
        </section>

        <!-- City Size / Cards Played -->
        <section class="stats-section">
          <h4 class="section-heading">City Progress</h4>
          <div class="stat-table">
            <div class="stat-row stat-header-row">
              <span class="stat-cell">Player</span>
              <span class="stat-cell">Cards</span>
              <span class="stat-cell">Season</span>
              <span class="stat-cell">Workers</span>
            </div>
            <div
              v-for="(player, i) in players"
              :key="player.id + '-city'"
              class="stat-row"
            >
              <span class="stat-cell stat-name" :style="{ color: playerColors[i % playerColors.length] }">
                {{ player.name }}
              </span>
              <span class="stat-cell">{{ player.city.length }} / 15</span>
              <span class="stat-cell stat-season">{{ player.season }}</span>
              <span class="stat-cell">
                {{ player.workers_placed }} / {{ player.workers_total }}
                <span class="utilization">({{ workerUtilization(player) }}%)</span>
              </span>
            </div>
          </div>
        </section>

        <!-- Turn Info -->
        <section class="stats-section stats-meta">
          <div class="meta-item">
            <span class="meta-label">Turn</span>
            <span class="meta-value">{{ store.state.turn_number }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">Deck</span>
            <span class="meta-value">{{ store.state.deck_size }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">Discard</span>
            <span class="meta-value">{{ store.state.discard_size }}</span>
          </div>
        </section>
      </div>

      <div v-else class="stats-empty">
        <p>Waiting for game state...</p>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.stats-toggle-btn {
  position: fixed;
  top: calc(50% + 56px);
  right: 0;
  z-index: 200;
  width: 32px;
  height: 48px;
  background: var(--parchment-dark);
  border: 1px solid var(--parchment-deep);
  border-right: none;
  border-radius: var(--radius-sm) 0 0 var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.2s ease;
}

.stats-toggle-btn:hover {
  background: var(--parchment-deep);
}

.stats-icon {
  font-size: 1rem;
}

.stats-panel {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 400px;
  max-width: 90vw;
  z-index: 201;
  background: rgba(244, 236, 224, 0.95);
  backdrop-filter: blur(8px);
  border-right: 2px solid var(--parchment-deep);
  box-shadow: 4px 0 24px rgba(44, 24, 16, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.stats-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--gap-md) var(--gap-lg);
  border-bottom: 1px solid var(--parchment-deep);
  background: var(--parchment-dark);
}

.stats-title {
  font-family: var(--font-display);
  font-size: 1.1rem;
  color: var(--forest-dark);
  margin: 0;
}

.stats-close {
  font-size: 1.5rem;
  color: var(--ink-faint);
  cursor: pointer;
  background: none;
  border: none;
  line-height: 1;
  padding: 0 4px;
  transition: color 0.2s ease;
}

.stats-close:hover {
  color: var(--ink);
}

.stats-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--gap-md) var(--gap-lg);
}

.stats-section {
  margin-bottom: var(--gap-lg);
}

.section-heading {
  font-family: var(--font-display);
  font-size: 0.82rem;
  color: var(--ink-faint);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: var(--gap-sm);
  padding-bottom: 4px;
  border-bottom: 1px solid var(--parchment-deep);
}

/* Bar chart */
.bar-chart {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.bar-row {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
}

.bar-label {
  width: 80px;
  font-size: 0.82rem;
  color: var(--ink-light);
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
  flex-shrink: 0;
}

.bar-track {
  flex: 1;
  height: 16px;
  background: var(--parchment-dark);
  border-radius: 3px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
  min-width: 2px;
}

.bar-value {
  width: 32px;
  text-align: right;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--ink);
  flex-shrink: 0;
}

/* Resource grid */
.resource-grid {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.resource-row {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
}

.res-player {
  width: 80px;
  font-size: 0.82rem;
  font-weight: 600;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
  flex-shrink: 0;
}

.res-items {
  display: flex;
  gap: var(--gap-md);
  font-size: 0.85rem;
}

.res-item {
  white-space: nowrap;
}

/* Stat table */
.stat-table {
  display: flex;
  flex-direction: column;
}

.stat-row {
  display: flex;
  padding: 4px 0;
  border-bottom: 1px solid var(--parchment-dark);
}

.stat-header-row {
  border-bottom: 1px solid var(--parchment-deep);
}

.stat-header-row .stat-cell {
  font-size: 0.72rem;
  color: var(--ink-faint);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  font-weight: 600;
}

.stat-cell {
  flex: 1;
  font-size: 0.82rem;
  color: var(--ink);
}

.stat-name {
  font-weight: 600;
}

.stat-season {
  text-transform: capitalize;
}

.utilization {
  font-size: 0.72rem;
  color: var(--ink-faint);
}

/* Meta */
.stats-meta {
  display: flex;
  gap: var(--gap-lg);
  padding-top: var(--gap-md);
  border-top: 1px solid var(--parchment-deep);
  margin-bottom: 0;
}

.meta-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.meta-label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--ink-faint);
}

.meta-value {
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--ink);
}

.stats-empty {
  padding: var(--gap-xl);
  text-align: center;
  color: var(--ink-faint);
  font-style: italic;
}

/* Slide transition */
.slide-left-enter-active,
.slide-left-leave-active {
  transition: transform 0.3s ease;
}

.slide-left-enter-from,
.slide-left-leave-to {
  transform: translateX(-100%);
}
</style>
