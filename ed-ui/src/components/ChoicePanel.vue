<script setup lang="ts">
import type { PendingChoice, PendingChoiceOption } from '../types'
import { RESOURCE_ICONS } from '../types'

const props = defineProps<{
  pendingChoice: PendingChoice
}>()

const emit = defineEmits<{
  (e: 'choose', index: number): void
}>()

function getOptionIcon(option: PendingChoiceOption): string {
  if (option.resource && option.resource in RESOURCE_ICONS) {
    return RESOURCE_ICONS[option.resource as keyof typeof RESOURCE_ICONS]
  }
  return ''
}

function getOptionClass(option: PendingChoiceOption): string {
  if (option.value === '__none__') return 'option-skip'
  if (option.resource) return `option-resource option-${option.resource}`
  if (option.source === 'hand') return 'option-hand'
  if (option.source === 'meadow') return 'option-meadow'
  return 'option-default'
}
</script>

<template>
  <div class="choice-panel">
    <div class="choice-header">
      <span class="choice-icon">&#9881;</span>
      <span class="choice-card-name">{{ pendingChoice.card }}</span>
      <span class="choice-prompt">{{ pendingChoice.prompt }}</span>
    </div>
    <div class="choice-options" v-if="pendingChoice.options">
      <button
        v-for="(option, index) in pendingChoice.options"
        :key="index"
        class="choice-option"
        :class="getOptionClass(option)"
        @click="emit('choose', index)"
      >
        <span v-if="getOptionIcon(option)" class="option-icon">{{ getOptionIcon(option) }}</span>
        <span class="option-label">{{ option.label }}</span>
        <span v-if="option.base_points !== undefined" class="option-points">{{ option.base_points }}pt</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.choice-panel {
  background: rgba(201, 169, 110, 0.12);
  border: 1.5px solid var(--gold);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  animation: pulse-glow 2s ease-in-out infinite;
}

.choice-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.choice-icon {
  font-size: 1rem;
}

.choice-card-name {
  font-family: var(--font-card);
  font-weight: 700;
  font-size: 0.85rem;
  color: var(--ink);
}

.choice-prompt {
  font-family: var(--font-display);
  font-size: 0.82rem;
  color: var(--ink-light);
}

.choice-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.choice-option {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 1.5px solid var(--parchment-deep);
  border-radius: var(--radius-md);
  background: white;
  font-family: var(--font-card);
  font-size: 0.85rem;
  color: var(--ink);
  cursor: pointer;
  transition: all 0.15s ease;
}

.choice-option:hover {
  border-color: var(--gold);
  background: rgba(201, 169, 110, 0.1);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.choice-option:active {
  transform: translateY(0);
}

.option-icon {
  font-size: 1.1rem;
}

.option-label {
  font-weight: 600;
}

.option-points {
  font-size: 0.75rem;
  color: var(--ink-faint);
  margin-left: 2px;
}

.option-skip {
  border-style: dashed;
  color: var(--ink-faint);
}

.option-skip:hover {
  border-color: var(--ink-faint);
  background: var(--parchment);
}

.option-resource.option-twig {
  border-color: #8B7355;
}

.option-resource.option-resin {
  border-color: #D4A017;
}

.option-resource.option-pebble {
  border-color: #808080;
}

.option-resource.option-berry {
  border-color: #C44569;
}

.option-hand {
  border-left: 3px solid var(--forest-light);
}

.option-meadow {
  border-left: 3px solid var(--gold);
}
</style>
