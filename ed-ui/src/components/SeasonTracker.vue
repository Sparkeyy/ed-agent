<script setup lang="ts">
import { SEASON_ORDER } from '../types'
import type { Season } from '../types'

defineProps<{
  season: string
  turnNumber: number
}>()

const seasonEmoji: Record<Season, string> = {
  winter: '\u2744\uFE0F',
  spring: '\u{1F331}',
  summer: '\u2600\uFE0F',
  autumn: '\u{1F342}',
}

const seasonLabels: Record<Season, string> = {
  winter: 'Winter',
  spring: 'Spring',
  summer: 'Summer',
  autumn: 'Autumn',
}
</script>

<template>
  <div class="season-tracker">
    <div class="seasons-row">
      <div
        v-for="s in SEASON_ORDER"
        :key="s"
        class="season-circle"
        :class="{ active: s === season }"
      >
        <span class="season-emoji">{{ seasonEmoji[s] }}</span>
        <span class="season-label">{{ seasonLabels[s] }}</span>
      </div>
    </div>
    <div class="turn-number">Turn {{ turnNumber }}</div>
  </div>
</template>

<style scoped>
.season-tracker {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--gap-xs);
}

.seasons-row {
  display: flex;
  gap: var(--gap-sm);
  align-items: center;
}

.season-circle {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 4px 8px;
  border-radius: var(--radius-md);
  opacity: 0.55;
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.season-circle.active {
  opacity: 1;
  transform: scale(1.2);
  background: var(--parchment-dark);
}

.season-emoji {
  font-size: 1.3rem;
}

.season-circle.active .season-emoji {
  font-size: 1.6rem;
}

.season-label {
  font-family: var(--font-display);
  font-size: 0.65rem;
  color: var(--ink-light);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.turn-number {
  font-family: var(--font-body);
  font-size: 0.75rem;
  color: var(--ink-faint);
}
</style>
