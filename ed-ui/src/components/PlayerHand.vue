<script setup lang="ts">
import type { CardData } from '../types'
import CardComponent from './CardComponent.vue'

const props = withDefaults(defineProps<{
  hand: CardData[]
  playableCardNames?: string[]
}>(), {
  playableCardNames: () => [],
})

const emit = defineEmits<{
  'play-from-hand': [cardName: string]
}>()

function isPlayable(cardName: string): boolean {
  return props.playableCardNames.includes(cardName)
}
</script>

<template>
  <div class="player-hand">
    <h3 class="hand-title">Your Hand <span class="hand-count">({{ hand.length }})</span></h3>
    <div class="hand-scroll">
      <CardComponent
        v-for="(card, index) in hand"
        :key="card.name + '-' + index"
        :card="card"
        :playable="isPlayable(card.name)"
        @select="isPlayable(card.name) && emit('play-from-hand', card.name)"
      />
      <div v-if="hand.length === 0" class="empty-hand">No cards in hand</div>
    </div>
  </div>
</template>

<style scoped>
.player-hand {
  padding: var(--gap-sm) var(--gap-md);
}

.hand-title {
  font-family: var(--font-display);
  font-size: 0.95rem;
  color: var(--ink);
  margin-bottom: var(--gap-sm);
}

.hand-count {
  font-family: var(--font-body);
  font-size: 0.75rem;
  font-weight: 400;
  color: var(--ink-faint);
}

.hand-scroll {
  display: flex;
  gap: var(--gap-sm);
  overflow-x: auto;
  padding-bottom: var(--gap-sm);
  scrollbar-width: thin;
  scrollbar-color: var(--parchment-deep) transparent;
}

.hand-scroll::-webkit-scrollbar {
  height: 6px;
}

.hand-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.hand-scroll::-webkit-scrollbar-thumb {
  background: var(--parchment-deep);
  border-radius: 3px;
}

.empty-hand {
  color: var(--ink-faint);
  font-style: italic;
  font-size: 0.85rem;
  padding: var(--gap-lg);
}
</style>
