<script setup lang="ts">
defineProps<{
  cards?: unknown[]
}>()
</script>

<template>
  <div class="meadow">
    <h3>Meadow</h3>
    <div class="meadow-grid">
      <div v-for="i in 8" :key="i" class="meadow-slot">
        <template v-if="cards && cards[i - 1]">
          {{ (cards[i - 1] as Record<string, unknown>).name || `Card ${i}` }}
        </template>
        <template v-else>
          Empty Slot {{ i }}
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.meadow {
  margin: 1rem 0;
}

.meadow-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.meadow-slot {
  border: 1px dashed #3a5a40;
  border-radius: 6px;
  padding: 1rem;
  text-align: center;
  background: #f5f0e8;
  min-height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
}
</style>
