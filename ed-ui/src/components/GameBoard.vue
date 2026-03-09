<script setup lang="ts">
import type { LocationData } from '../types'

const props = withDefaults(defineProps<{
  basicLocations: LocationData[]
  forestLocations: LocationData[]
  validLocationIds?: string[]
}>(), {
  validLocationIds: () => [],
})

const emit = defineEmits<{
  'place-worker': [locationId: string]
}>()

function isValid(id: string): boolean {
  return props.validLocationIds.includes(id)
}

// Simple color hash for worker dots
function workerColor(workerId: string): string {
  const colors = ['#4a7c59', '#a83832', '#3a6b8c', '#6b4c7a']
  let hash = 0
  for (const ch of workerId) hash = (hash * 31 + ch.charCodeAt(0)) & 0xffffff
  return colors[hash % colors.length]
}
</script>

<template>
  <div class="game-board">
    <div class="board-section">
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
          <div class="location-type">{{ loc.location_type }}</div>
          <div v-if="loc.workers.length > 0" class="location-workers">
            <span
              v-for="(worker, wi) in loc.workers"
              :key="wi"
              class="worker-circle"
              :style="{ backgroundColor: workerColor(worker) }"
            ></span>
          </div>
          <div v-if="loc.exclusive" class="exclusive-badge">1</div>
        </div>
      </div>
    </div>

    <div class="board-section">
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
          <div class="location-type">{{ loc.location_type }}</div>
          <div v-if="loc.workers.length > 0" class="location-workers">
            <span
              v-for="(worker, wi) in loc.workers"
              :key="wi"
              class="worker-circle"
              :style="{ backgroundColor: workerColor(worker) }"
            ></span>
          </div>
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
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
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
  background: var(--green-production-bg);
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
  gap: 3px;
  margin-top: var(--gap-xs);
}

.worker-circle {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.6);
}

.exclusive-badge {
  position: absolute;
  top: 4px;
  right: 6px;
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
