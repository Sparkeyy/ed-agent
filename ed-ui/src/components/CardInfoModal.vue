<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { RESOURCE_IMAGES } from '../types'
import type { ResourceBank } from '../types'

const CARD_TYPE_COLORS: Record<string, string> = {
  tan_traveler: '#a08060',
  green_production: '#4a7c59',
  red_destination: '#a83832',
  blue_governance: '#3a6b8c',
  purple_prosperity: '#6b4c7a',
}

const CARD_TYPE_NAMES: Record<string, string> = {
  tan_traveler: 'Traveler',
  green_production: 'Production',
  red_destination: 'Destination',
  blue_governance: 'Governance',
  purple_prosperity: 'Prosperity',
}

const props = defineProps<{
  visible: boolean
  title: string
  subtitle?: string
  cardType?: string
  category?: string
  description?: string
  ability?: string
  cost?: ResourceBank
  points?: number
}>()

const emit = defineEmits<{
  close: []
}>()

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => window.removeEventListener('keydown', handleKeydown))

function costEntries(cost: ResourceBank): Array<{ key: string; count: number }> {
  const entries: Array<{ key: string; count: number }> = []
  for (const key of ['twig', 'resin', 'pebble', 'berry'] as (keyof ResourceBank)[]) {
    if (cost[key] > 0) entries.push({ key, count: cost[key] })
  }
  return entries
}
</script>

<template>
  <Transition name="modal-fade">
    <div v-if="visible" class="modal-backdrop" @click.self="emit('close')">
      <div class="modal-card">
        <button class="modal-close" @click="emit('close')">&times;</button>

        <div class="modal-type-bar" v-if="cardType" :style="{ backgroundColor: CARD_TYPE_COLORS[cardType] || '#888' }">
          <span class="type-label">{{ CARD_TYPE_NAMES[cardType] || cardType }}</span>
          <span v-if="category" class="cat-label">{{ category }}</span>
        </div>

        <div class="modal-body">
          <h2 class="modal-title">{{ title }}</h2>

          <div v-if="subtitle" class="modal-subtitle">{{ subtitle }}</div>

          <div v-if="cost" class="modal-cost">
            <span class="cost-label">Cost:</span>
            <span v-for="entry in costEntries(cost)" :key="entry.key" class="cost-item">
              <img :src="RESOURCE_IMAGES[entry.key as keyof typeof RESOURCE_IMAGES]" :alt="entry.key" class="cost-icon">
              <span>{{ entry.count }}</span>
            </span>
            <span v-if="costEntries(cost).length === 0" class="cost-free">Free</span>
          </div>

          <div v-if="points !== undefined" class="modal-points">
            <span class="vp-badge">VP</span> {{ points }}
          </div>

          <p v-if="description" class="modal-desc">{{ description }}</p>

          <div v-if="ability" class="modal-ability">
            <span class="ability-label">Ability</span>
            <p class="ability-text">{{ ability }}</p>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(26, 47, 26, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 300;
}

.modal-card {
  background: var(--parchment, #f4ece0);
  border-radius: var(--radius-lg, 12px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  max-width: 380px;
  width: 90%;
  overflow: hidden;
  position: relative;
}

.modal-close {
  position: absolute;
  top: 8px;
  right: 10px;
  font-size: 1.5rem;
  color: rgba(255, 255, 255, 0.8);
  cursor: pointer;
  background: none;
  border: none;
  z-index: 1;
  line-height: 1;
}

.modal-close:hover {
  color: white;
}

.modal-type-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  color: white;
}

.type-label {
  font-family: var(--font-display, serif);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 700;
}

.cat-label {
  font-size: 0.7rem;
  text-transform: capitalize;
  opacity: 0.85;
}

.modal-body {
  padding: 16px 20px 20px;
}

.modal-title {
  font-family: var(--font-display, serif);
  font-size: 1.3rem;
  color: var(--ink, #2c1810);
  margin-bottom: 4px;
}

.modal-subtitle {
  font-size: 0.78rem;
  color: var(--ink-faint, #8b7a6b);
  margin-bottom: 8px;
}

.modal-cost {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.cost-label {
  font-size: 0.75rem;
  color: var(--ink-faint, #8b7a6b);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.cost-item {
  display: flex;
  align-items: center;
  gap: 2px;
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--ink, #2c1810);
}

.cost-icon {
  width: 18px;
  height: 18px;
  object-fit: contain;
}

.cost-free {
  font-style: italic;
  color: var(--ink-faint, #8b7a6b);
  font-size: 0.85rem;
}

.modal-points {
  font-size: 1rem;
  font-weight: 700;
  color: var(--ink, #2c1810);
  margin-bottom: 12px;
}

.vp-badge {
  display: inline-block;
  background: #b8860b;
  color: white;
  font-size: 0.55rem;
  font-weight: 700;
  padding: 2px 4px;
  border-radius: 3px;
  vertical-align: middle;
}

.modal-desc {
  font-size: 0.88rem;
  color: var(--ink-light, #5a4a3a);
  line-height: 1.5;
  font-style: italic;
  margin-bottom: 12px;
}

.modal-ability {
  background: rgba(74, 124, 89, 0.08);
  border: 1px solid rgba(74, 124, 89, 0.2);
  border-radius: var(--radius-md, 8px);
  padding: 10px 14px;
}

.ability-label {
  display: block;
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--forest-mid, #3a5a44);
  font-weight: 700;
  margin-bottom: 4px;
}

.ability-text {
  font-size: 0.88rem;
  color: var(--ink, #2c1810);
  line-height: 1.5;
  margin: 0;
}

/* Transition */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}
.modal-fade-enter-active .modal-card,
.modal-fade-leave-active .modal-card {
  transition: transform 0.2s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
.modal-fade-enter-from .modal-card,
.modal-fade-leave-to .modal-card {
  transform: scale(0.95);
}
</style>
