<script setup lang="ts">
import type { CardData, ResourceBank } from '../types'
import { CARD_TYPE_LABELS, RESOURCE_ICONS } from '../types'

withDefaults(defineProps<{
  card: CardData
  compact?: boolean
  playable?: boolean
  selected?: boolean
}>(), {
  compact: false,
  playable: false,
  selected: false,
})

const emit = defineEmits<{
  select: []
}>()

const categoryIcon = (cat: string) => cat === 'critter' ? '\u{1F43F}\u{FE0F}' : '\u{1F3D7}\u{FE0F}'

function cardColorVar(cardType: string): string {
  return `var(--${cardType.replace('_', '-')})`
}

function costEntries(cost: ResourceBank): Array<{ key: string; icon: string; count: number }> {
  const entries: Array<{ key: string; icon: string; count: number }> = []
  const keys: (keyof ResourceBank)[] = ['twig', 'resin', 'pebble', 'berry']
  for (const key of keys) {
    if (cost[key] > 0) {
      entries.push({ key, icon: RESOURCE_ICONS[key], count: cost[key] })
    }
  }
  return entries
}
</script>

<template>
  <div
    :class="[
      'card',
      `card-type-${card.card_type}`,
      { compact, playable, selected },
    ]"
    @click="emit('select')"
  >
    <template v-if="compact">
      <span class="compact-name">{{ card.name }}</span>
      <span class="compact-points">\u2B50 {{ card.base_points }}</span>
    </template>
    <template v-else>
      <div class="card-top-bar" :style="{ backgroundColor: cardColorVar(card.card_type) }"></div>
      <div class="card-body">
        <div class="card-name">{{ card.name }}</div>
        <div class="card-meta">
          <span class="card-category">{{ categoryIcon(card.category) }}</span>
          <span class="card-type-label">{{ CARD_TYPE_LABELS[card.card_type] }}</span>
          <span v-if="card.unique" class="unique-badge">\u2726</span>
        </div>
        <div class="card-cost">
          <span v-for="entry in costEntries(card.cost)" :key="entry.key" class="cost-item">
            {{ entry.icon }}<span class="cost-num">{{ entry.count }}</span>
          </span>
          <span v-if="costEntries(card.cost).length === 0" class="cost-free">Free</span>
        </div>
        <div class="card-points">\u2B50 {{ card.base_points }}</div>
        <div v-if="card.paired_with" class="card-paired">
          Paired: {{ card.paired_with }}
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.card {
  width: 140px;
  height: 190px;
  background: var(--card-bg, #fffdf8);
  border: var(--border-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  position: relative;
  flex-shrink: 0;
}

.card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.card.playable {
  animation: pulse-glow 2s ease-in-out infinite;
  cursor: pointer;
}

.card.selected {
  border: 2px solid var(--gold-bright);
  transform: scale(1.04);
  box-shadow: var(--shadow-glow);
}

/* Compact mode */
.card.compact {
  width: 100px;
  height: 36px;
  flex-direction: row;
  align-items: center;
  padding: 0 var(--gap-sm);
  gap: var(--gap-xs);
  border-left: 3px solid var(--card-color, var(--ink-faint));
  border-radius: var(--radius-sm);
}

.compact-name {
  font-family: var(--font-card);
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--ink);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.compact-points {
  font-size: 0.65rem;
  color: var(--ink-faint);
  flex-shrink: 0;
}

/* Full card */
.card-top-bar {
  height: 4px;
  width: 100%;
  flex-shrink: 0;
}

.card-body {
  padding: var(--gap-sm);
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.card-name {
  font-family: var(--font-card);
  font-weight: 700;
  font-size: 0.82rem;
  color: var(--ink);
  line-height: 1.2;
  text-align: center;
}

.card-meta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 0.68rem;
  color: var(--ink-light);
}

.card-category {
  font-size: 0.8rem;
}

.card-type-label {
  font-family: var(--font-body);
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.unique-badge {
  color: var(--gold);
  font-size: 0.85rem;
}

.card-cost {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: auto;
}

.cost-item {
  font-size: 0.8rem;
  display: flex;
  align-items: center;
  gap: 1px;
}

.cost-num {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--ink-light);
}

.cost-free {
  font-size: 0.68rem;
  color: var(--ink-faint);
  font-style: italic;
}

.card-points {
  text-align: center;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--ink);
}

.card-paired {
  font-size: 0.6rem;
  color: var(--ink-faint);
  text-align: center;
  font-style: italic;
}
</style>
