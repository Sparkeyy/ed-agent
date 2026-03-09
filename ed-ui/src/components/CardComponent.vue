<script setup lang="ts">
defineProps<{
  card: {
    name?: string
    type?: string
    cost?: Record<string, number>
    points?: number
  }
}>()
</script>

<template>
  <div class="card">
    <div class="card-header">{{ card.name || 'Unknown Card' }}</div>
    <div class="card-type">{{ card.type || '' }}</div>
    <div class="card-points" v-if="card.points !== undefined">{{ card.points }} VP</div>
  </div>
</template>

<style scoped>
.card {
  width: 120px;
  height: 170px;
  border: 2px solid #3a5a40;
  border-radius: 8px;
  background: white;
  padding: 0.5rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  font-size: 0.8rem;
}

.card-header {
  font-weight: bold;
  text-align: center;
}

.card-type {
  text-align: center;
  color: #666;
  font-size: 0.7rem;
}

.card-points {
  text-align: center;
  font-weight: bold;
  color: #3a5a40;
}
</style>
