<script setup lang="ts">
import { ref } from 'vue'
import type { ResourceBank } from '../types'
import { RESOURCE_ICONS, RESOURCE_IMAGES } from '../types'

withDefaults(defineProps<{
  resources: ResourceBank
  compact?: boolean
}>(), {
  compact: false,
})

const resourceKeys: (keyof ResourceBank)[] = ['twig', 'resin', 'pebble', 'berry']

const resourceLabels: Record<keyof ResourceBank, string> = {
  twig: 'Twigs',
  resin: 'Resin',
  pebble: 'Pebbles',
  berry: 'Berries',
}

const imgFailed = ref<Record<string, boolean>>({})
</script>

<template>
  <div class="resource-display" :class="{ compact }">
    <div
      v-for="key in resourceKeys"
      :key="key"
      class="resource-item"
    >
      <img
        v-if="!imgFailed[key]"
        :src="RESOURCE_IMAGES[key]"
        :alt="resourceLabels[key]"
        class="resource-icon resource-img"
        @error="imgFailed[key] = true"
      >
      <span v-else class="resource-icon">{{ RESOURCE_ICONS[key] }}</span>
      <span class="resource-count">{{ resources[key] }}</span>
      <span v-if="!compact" class="resource-label">{{ resourceLabels[key] }}</span>
    </div>
  </div>
</template>

<style scoped>
.resource-display {
  display: flex;
  gap: var(--gap-md);
  align-items: center;
}

.resource-display.compact {
  gap: var(--gap-sm);
}

.resource-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: var(--parchment-dark);
  border-radius: var(--radius-sm);
  transition: background 0.3s ease;
}

.compact .resource-item {
  padding: 2px 6px;
  background: transparent;
}

.resource-icon {
  font-size: 1rem;
}

.resource-img {
  width: 20px;
  height: 20px;
  object-fit: contain;
}

.compact .resource-icon {
  font-size: 0.85rem;
}

.compact .resource-img {
  width: 16px;
  height: 16px;
}

.resource-count {
  font-weight: 700;
  font-size: 1rem;
  color: var(--ink);
  transition: transform 0.3s ease;
  min-width: 1ch;
  text-align: center;
}

.compact .resource-count {
  font-size: 0.85rem;
}

.resource-label {
  font-size: 0.7rem;
  color: var(--ink-faint);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
</style>
