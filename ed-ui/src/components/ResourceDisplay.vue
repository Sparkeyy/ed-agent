<script setup lang="ts">
defineProps<{
  resources: Record<string, number>
}>()

const resourceLabels: Record<string, string> = {
  twig: 'Twigs',
  resin: 'Resin',
  pebble: 'Pebbles',
  berry: 'Berries',
}
</script>

<template>
  <div class="resource-display">
    <div
      v-for="(count, key) in resources"
      :key="key"
      class="resource-item"
    >
      <span class="resource-label">{{ resourceLabels[key as string] || key }}</span>
      <span class="resource-count">{{ count }}</span>
    </div>
  </div>
</template>

<style scoped>
.resource-display {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.resource-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: white;
  border: 1px solid #ccc;
  border-radius: 6px;
  min-width: 60px;
}

.resource-label {
  font-size: 0.7rem;
  color: #666;
}

.resource-count {
  font-size: 1.2rem;
  font-weight: bold;
  color: #3a5a40;
}
</style>
