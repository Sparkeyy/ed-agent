<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
const gameId = route.params.id as string
</script>

<template>
  <div class="score-view">
    <h2>Score Screen</h2>
    <p>Game ID: <code>{{ gameId }}</code></p>
    <p>Final scores will be displayed here.</p>
  </div>
</template>

<style scoped>
.score-view {
  text-align: center;
  padding: 2rem;
}

code {
  background: #e0d8cc;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}
</style>
