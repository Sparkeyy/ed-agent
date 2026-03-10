<script setup lang="ts">
import type { CardData } from '../types'
import CardComponent from './CardComponent.vue'

const props = withDefaults(defineProps<{
  meadow: CardData[]
  playableIndices?: number[]
}>(), {
  playableIndices: () => [],
})

const emit = defineEmits<{
  'play-from-meadow': [index: number]
  'card-info': [cardName: string]
}>()

function isPlayable(index: number): boolean {
  return props.playableIndices.includes(index)
}
</script>

<template>
  <div class="meadow-section">
    <h3 class="meadow-title">The Meadow</h3>
    <div class="meadow-grid">
      <div
        v-for="(card, index) in meadow"
        :key="index"
        class="meadow-slot"
      >
        <CardComponent
          :card="card"
          :playable="isPlayable(index)"
          :fill="true"
          @select="isPlayable(index) && emit('play-from-meadow', index)"
          @info="emit('card-info', $event)"
        />
      </div>
      <!-- Fill remaining slots if less than 8 -->
      <div
        v-for="i in Math.max(0, 8 - meadow.length)"
        :key="'empty-' + i"
        class="meadow-slot meadow-empty"
      >
        <div class="empty-slot">Empty</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.meadow-section {
  padding: var(--gap-md);
  background: linear-gradient(135deg, rgba(74, 124, 89, 0.06), rgba(74, 124, 89, 0.02));
  border: 1.5px solid rgba(74, 124, 89, 0.2);
  border-radius: var(--radius-lg);
}

.meadow-title {
  font-family: var(--font-display);
  font-size: 1.1rem;
  color: var(--forest-mid);
  margin-bottom: var(--gap-sm);
  text-align: center;
}

.meadow-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--gap-md);
  justify-items: center;
}

.meadow-slot {
  display: flex;
  justify-content: center;
}

.empty-slot {
  width: clamp(100px, 11vw, 150px);
  height: clamp(140px, 15vw, 200px);
  border: 1.5px dashed var(--parchment-deep);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink-faint);
  font-size: 0.7rem;
  font-style: italic;
  opacity: 0.4;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

@media (max-width: 768px) {
  .meadow-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
