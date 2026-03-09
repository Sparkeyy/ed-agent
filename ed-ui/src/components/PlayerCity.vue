<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import type { PlayerData } from '../types'
import CardComponent from './CardComponent.vue'

const props = withDefaults(defineProps<{
  player: PlayerData
  isMe?: boolean
  gameId?: string
}>(), {
  isMe: false,
  gameId: '',
})

const emit = defineEmits<{
  'card-info': [cardName: string]
}>()

const MAX_CITY_SIZE = 15
const GRID_SNAP = 8
const CARD_W = 104
const CARD_H = 40
const COLS = 5

// Card positions for draggable layout (my city only)
const positions = ref<Record<string, { x: number; y: number }>>({})
const dragging = ref<string | null>(null)
const dragOffset = ref({ x: 0, y: 0 })

const storageKey = computed(() => `everdell_city_layout_${props.gameId}_${props.player.id}`)

// Load positions from localStorage
function loadPositions() {
  if (!props.isMe) return
  try {
    const raw = localStorage.getItem(storageKey.value)
    if (raw) positions.value = JSON.parse(raw)
  } catch { /* ignore */ }
}

function savePositions() {
  if (!props.isMe) return
  localStorage.setItem(storageKey.value, JSON.stringify(positions.value))
}

// Auto-assign positions for new cards
function ensurePositions() {
  let changed = false
  for (let i = 0; i < props.player.city.length; i++) {
    const name = props.player.city[i].name
    // Use index-based key to handle duplicate card names
    const key = `${name}_${i}`
    if (!positions.value[key]) {
      const col = i % COLS
      const row = Math.floor(i / COLS)
      positions.value[key] = {
        x: col * (CARD_W + GRID_SNAP),
        y: row * (CARD_H + GRID_SNAP),
      }
      changed = true
    }
  }
  if (changed) savePositions()
}

watch(() => props.player.city.length, () => ensurePositions(), { immediate: true })
watch(() => storageKey.value, () => { loadPositions(); ensurePositions() }, { immediate: true })

function cardKey(index: number): string {
  return `${props.player.city[index].name}_${index}`
}

// Drag handlers
function onMouseDown(e: MouseEvent, index: number) {
  if (!props.isMe) return
  e.preventDefault()
  const key = cardKey(index)
  dragging.value = key
  const pos = positions.value[key] || { x: 0, y: 0 }
  dragOffset.value = { x: e.clientX - pos.x, y: e.clientY - pos.y }
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
}

function onMouseMove(e: MouseEvent) {
  if (!dragging.value) return
  let x = e.clientX - dragOffset.value.x
  let y = e.clientY - dragOffset.value.y
  // Snap to grid
  x = Math.round(x / GRID_SNAP) * GRID_SNAP
  y = Math.round(y / GRID_SNAP) * GRID_SNAP
  positions.value[dragging.value] = { x, y }
}

function onMouseUp() {
  dragging.value = null
  savePositions()
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
}

// Container size
const containerHeight = computed(() => {
  if (!props.isMe) return 'auto'
  let maxY = CARD_H * 3
  for (const pos of Object.values(positions.value)) {
    maxY = Math.max(maxY, pos.y + CARD_H + 8)
  }
  return `${maxY}px`
})

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

    <!-- Draggable layout for my city -->
    <div v-if="isMe" class="city-canvas" :style="{ minHeight: containerHeight }">
      <div
        v-for="(card, index) in player.city"
        :key="cardKey(index)"
        class="city-card-wrapper"
        :class="{ dragging: dragging === cardKey(index) }"
        :style="{
          transform: `translate(${(positions[cardKey(index)]?.x ?? 0)}px, ${(positions[cardKey(index)]?.y ?? 0)}px)`,
        }"
        @mousedown="onMouseDown($event, index)"
      >
        <CardComponent
          :card="card"
          :compact="true"
          @info="emit('card-info', $event)"
        />
        <div v-if="isDestination(card)" class="destination-marker" :class="{ visited: destinationVisited(card.name) }">
          <span class="dest-icon">W</span>
        </div>
        <div v-if="workerDotsForCard(card.name) > 0" class="worker-dots">
          <span v-for="w in workerDotsForCard(card.name)" :key="w" class="worker-dot"></span>
        </div>
      </div>
    </div>

    <!-- Static grid for opponent cities -->
    <div v-else class="city-grid">
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
            @info="emit('card-info', $event)"
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

/* Draggable canvas for my city */
.city-canvas {
  position: relative;
  background-image: radial-gradient(circle, var(--parchment-deep) 1px, transparent 1px);
  background-size: 8px 8px;
  border: 1px dashed var(--parchment-deep);
  border-radius: var(--radius-md);
  min-height: 120px;
  overflow: visible;
}

.city-card-wrapper {
  position: absolute;
  cursor: grab;
  user-select: none;
  transition: box-shadow 0.15s ease;
  z-index: 1;
}

.city-card-wrapper:hover {
  z-index: 2;
}

.city-card-wrapper.dragging {
  cursor: grabbing;
  z-index: 10;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

/* Static grid for opponents */
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
