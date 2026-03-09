<script setup lang="ts">
import type { PlayerData } from '../types'
import CardComponent from './CardComponent.vue'

const props = withDefaults(defineProps<{
  player: PlayerData
  isMe?: boolean
}>(), {
  isMe: false,
})

const MAX_CITY_SIZE = 15

function workerDotsForCard(cardName: string): number {
  return props.player.workers_deployed.filter(loc => loc === `destination:${cardName}`).length
}

function isDestination(card: any): boolean {
  return card?.is_open_destination === true
}

function destinationVisited(cardName: string): boolean {
  return props.player.workers_deployed.includes(`destination:${cardName}`)
}
</script>

<template>
  <div class="player-city" :class="{ 'is-me': isMe }">
    <div class="city-header">
      <h3 class="city-title">City of {{ player.name }}</h3>
      <span class="city-count">{{ player.city.length }}/{{ MAX_CITY_SIZE }}</span>
    </div>
    <div class="city-grid">
      <div
        v-for="i in MAX_CITY_SIZE"
        :key="i"
        class="city-slot"
        :class="{ occupied: player.city[i - 1] }"
      >
        <template v-if="player.city[i - 1]">
          <CardComponent
            :card="player.city[i - 1]"
            :compact="true"
          />
          <div v-if="isDestination(player.city[i - 1])" class="destination-marker" :class="{ visited: destinationVisited(player.city[i - 1].name) }">
            <span class="dest-icon">W</span>
          </div>
          <div
            v-if="workerDotsForCard(player.city[i - 1].name) > 0"
            class="worker-dots"
          >
            <span
              v-for="w in workerDotsForCard(player.city[i - 1].name)"
              :key="w"
              class="worker-dot"
            ></span>
          </div>
        </template>
        <template v-else>
          <div class="empty-city-slot"></div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.player-city {
  padding: var(--gap-sm) var(--gap-md);
}

.player-city.is-me {
  background: rgba(201, 169, 110, 0.06);
  border-radius: var(--radius-md);
}

.city-header {
  display: flex;
  align-items: baseline;
  gap: var(--gap-sm);
  margin-bottom: var(--gap-sm);
}

.city-title {
  font-family: var(--font-display);
  font-size: 0.95rem;
  color: var(--ink);
}

.city-count {
  font-size: 0.75rem;
  color: var(--ink-faint);
  font-family: var(--font-body);
}

.city-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  grid-template-rows: repeat(3, auto);
  gap: var(--gap-xs);
}

.city-slot {
  position: relative;
  min-height: 36px;
}

.city-slot.occupied {
  display: flex;
  align-items: center;
}

.empty-city-slot {
  width: 100px;
  height: 36px;
  border: 1.5px dashed var(--parchment-deep);
  border-radius: var(--radius-sm);
  opacity: 0.5;
}

.worker-dots {
  position: absolute;
  top: -4px;
  right: -2px;
  display: flex;
  gap: 2px;
}

.worker-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--forest-light);
  border: 1px solid white;
}

.destination-marker {
  position: absolute;
  bottom: -2px;
  right: -2px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--red-destination, #a83832);
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid white;
}

.destination-marker.visited {
  background: var(--ink-faint);
  opacity: 0.5;
}

.dest-icon {
  font-size: 0.5rem;
  font-weight: 700;
  color: white;
}
</style>
