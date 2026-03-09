<script setup lang="ts">
defineProps<{
  playerName?: string
  city?: unknown[]
}>()
</script>

<template>
  <div class="player-city">
    <h3>{{ playerName || 'Player' }}'s City</h3>
    <div class="city-grid">
      <div v-for="i in 15" :key="i" class="city-slot">
        <template v-if="city && city[i - 1]">
          {{ (city[i - 1] as Record<string, unknown>).name || `Building ${i}` }}
        </template>
        <template v-else>
          {{ i }}
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.player-city {
  margin: 1rem 0;
}

.city-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  grid-template-rows: repeat(3, 1fr);
  gap: 0.4rem;
  margin-top: 0.5rem;
}

.city-slot {
  border: 1px solid #a08060;
  border-radius: 4px;
  padding: 0.75rem;
  text-align: center;
  background: white;
  min-height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  color: #999;
}
</style>
