<script setup lang="ts">
import type { LocationData } from '../types'

const props = withDefaults(defineProps<{
  basicLocations: LocationData[]
  forestLocations: LocationData[]
  havenLocations?: LocationData[]
  journeyLocations?: LocationData[]
  validLocationIds?: string[]
  playerNames?: Record<string, string>
  playerOrder?: string[]
  currentSeason?: string
}>(), {
  havenLocations: () => [],
  journeyLocations: () => [],
  validLocationIds: () => [],
  playerNames: () => ({}),
  playerOrder: () => [],
  currentSeason: 'winter',
})

const emit = defineEmits<{
  'place-worker': [locationId: string]
  'location-info': [locationId: string]
}>()

function isValid(id: string): boolean {
  return props.validLocationIds.includes(id)
}

// Distinct player colors — high contrast, won't blend with location backgrounds
const PLAYER_COLORS = ['#e07020', '#2196f3', '#e53980', '#00a86b']
function workerColor(workerId: string): string {
  const idx = props.playerOrder.indexOf(workerId)
  if (idx >= 0) return PLAYER_COLORS[idx % PLAYER_COLORS.length]
  return '#888'
}

function workerLabel(workerId: string): string {
  const name = props.playerNames[workerId]
  if (name) return name.substring(0, 2).toUpperCase()
  return '??'
}

function workerTitle(workerId: string): string {
  return props.playerNames[workerId] || workerId
}
</script>

<template>
  <div class="game-board">
    <div v-if="basicLocations.length > 0" class="board-section">
      <h3 class="section-title">Basic Locations</h3>
      <div class="locations-grid basic-grid">
        <div
          v-for="loc in basicLocations"
          :key="loc.id"
          class="location"
          :class="{ valid: isValid(loc.id), exclusive: loc.exclusive }"
          @click="isValid(loc.id) && emit('place-worker', loc.id)"
        >
          <div class="location-name">{{ loc.name }}</div>
          <div class="location-type">{{ loc.exclusive ? 'Closed' : 'Open' }}</div>
          <div v-if="loc.workers.length > 0" class="location-workers">
            <span
              v-for="(worker, wi) in loc.workers"
              :key="wi"
              class="worker-token"
              :style="{ backgroundColor: workerColor(worker) }"
              :title="workerTitle(worker)"
            >{{ workerLabel(worker) }}</span>
          </div>
          <div v-if="loc.exclusive" class="exclusive-badge">1</div>
          <button class="loc-info-btn" @click.stop="emit('location-info', loc.id)" title="Location info">i</button>
        </div>
      </div>
    </div>

    <div v-if="forestLocations.length > 0" class="board-section">
      <h3 class="section-title">Forest Locations</h3>
      <div class="locations-grid forest-grid">
        <div
          v-for="loc in forestLocations"
          :key="loc.id"
          class="location forest-location"
          :class="{ valid: isValid(loc.id) }"
          @click="isValid(loc.id) && emit('place-worker', loc.id)"
        >
          <div class="location-name">{{ loc.name }}</div>
          <div class="location-type">Exclusive</div>
          <div v-if="loc.workers.length > 0" class="location-workers">
            <span
              v-for="(worker, wi) in loc.workers"
              :key="wi"
              class="worker-token"
              :style="{ backgroundColor: workerColor(worker) }"
              :title="workerTitle(worker)"
            >{{ workerLabel(worker) }}</span>
          </div>
          <button class="loc-info-btn" @click.stop="emit('location-info', loc.id)" title="Location info">i</button>
        </div>
      </div>
    </div>

    <div v-if="havenLocations.length > 0" class="board-section">
      <h3 class="section-title">Haven</h3>
      <div class="locations-grid haven-grid">
        <div
          v-for="loc in havenLocations"
          :key="loc.id"
          class="location haven-location"
          :class="{ valid: isValid(loc.id) }"
          @click="isValid(loc.id) && emit('place-worker', loc.id)"
        >
          <div class="location-name">{{ loc.name }}</div>
          <div class="location-type">Discard 2 cards → 1 any resource</div>
          <div v-if="loc.workers.length > 0" class="location-workers">
            <span
              v-for="(worker, wi) in loc.workers"
              :key="wi"
              class="worker-token"
              :style="{ backgroundColor: workerColor(worker) }"
              :title="workerTitle(worker)"
            >{{ workerLabel(worker) }}</span>
          </div>
          <button class="loc-info-btn" @click.stop="emit('location-info', loc.id)" title="Location info">i</button>
        </div>
      </div>
    </div>

    <div v-if="journeyLocations.length > 0" class="board-section">
      <h3 class="section-title">Journey <span class="journey-note">(Autumn only)</span></h3>
      <div class="locations-grid journey-grid">
        <div
          v-for="loc in journeyLocations"
          :key="loc.id"
          class="location journey-location"
          :class="{ valid: isValid(loc.id), disabled: currentSeason !== 'autumn' }"
          @click="isValid(loc.id) && emit('place-worker', loc.id)"
        >
          <div class="location-name">{{ loc.name }}</div>
          <div class="location-type">{{ loc.exclusive ? 'Exclusive' : 'Open' }}</div>
          <div v-if="loc.workers.length > 0" class="location-workers">
            <span
              v-for="(worker, wi) in loc.workers"
              :key="wi"
              class="worker-token"
              :style="{ backgroundColor: workerColor(worker) }"
              :title="workerTitle(worker)"
            >{{ workerLabel(worker) }}</span>
          </div>
          <button class="loc-info-btn" @click.stop="emit('location-info', loc.id)" title="Location info">i</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.game-board {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  padding: var(--gap-md);
}

.board-section {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.section-title {
  font-family: var(--font-display);
  font-size: 1rem;
  color: var(--forest-mid);
}

.locations-grid {
  display: grid;
  gap: var(--gap-sm);
}

.basic-grid {
  display: flex;
  flex-wrap: nowrap;
  overflow-x: auto;
}

@media (max-width: 768px) {
  .basic-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    overflow-x: visible;
  }
}

.loc-info-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1.5px solid var(--ink-faint);
  background: rgba(255, 255, 255, 0.8);
  color: var(--ink-faint);
  font-size: 0.55rem;
  font-weight: 700;
  font-style: italic;
  font-family: serif;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  opacity: 0;
  transition: opacity 0.15s ease;
  z-index: 1;
}

.location:hover .loc-info-btn {
  opacity: 1;
}

.loc-info-btn:hover {
  background: var(--gold);
  color: white;
  border-color: var(--gold);
}

.forest-grid {
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
}

.location {
  position: relative;
  padding: var(--gap-sm) var(--gap-md);
  background: var(--parchment-dark);
  border: 1.5px solid var(--parchment-deep);
  border-radius: var(--radius-lg);
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
  min-width: clamp(120px, 12vw, 170px);
  flex-shrink: 0;
}

.location.valid {
  animation: pulse-glow 2s ease-in-out infinite;
  border-color: var(--gold);
  cursor: pointer;
}

.location.valid:hover {
  box-shadow: var(--shadow-glow);
  transform: translateY(-1px);
}

.forest-location {
  background: rgba(74, 124, 89, 0.12);
  border-color: rgba(74, 124, 89, 0.3);
}

.location-name {
  font-family: var(--font-card);
  font-weight: 600;
  font-size: 0.82rem;
  color: var(--ink);
  margin-bottom: 2px;
}

.location-type {
  font-size: 0.68rem;
  color: var(--ink-faint);
  text-transform: capitalize;
}

.location-workers {
  display: flex;
  gap: 4px;
  margin-top: var(--gap-xs);
  flex-wrap: wrap;
}

.worker-token {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 26px;
  height: 20px;
  padding: 0 4px;
  border-radius: 10px;
  font-size: 0.6rem;
  font-weight: 700;
  color: white;
  border: 1.5px solid rgba(255, 255, 255, 0.7);
  letter-spacing: 0.02em;
}

.haven-location {
  background: var(--parchment);
  border-color: rgba(100, 140, 180, 0.4);
}

.journey-location {
  background: rgba(180, 140, 60, 0.1);
  border-color: rgba(180, 140, 60, 0.4);
}

.journey-location.disabled {
  opacity: 0.4;
}

.journey-note {
  font-size: 0.7rem;
  font-weight: 400;
  color: var(--ink-faint);
  font-style: italic;
}

.haven-grid {
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
}

.journey-grid {
  display: flex;
  flex-wrap: nowrap;
  overflow-x: auto;
}

.exclusive-badge {
  position: absolute;
  top: 4px;
  left: 6px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--ink-faint);
  color: white;
  font-size: 0.55rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
