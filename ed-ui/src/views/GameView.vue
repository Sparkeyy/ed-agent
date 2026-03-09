<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useGameStore } from '../stores/game'

const route = useRoute()
const store = useGameStore()

const gameId = route.params.id as string

onMounted(() => {
  store.connect(gameId)
})

onUnmounted(() => {
  store.disconnect()
})
</script>

<template>
  <div class="game-view">
    <h2>Game Board - Coming Soon</h2>
    <p>Game ID: <code>{{ gameId }}</code></p>
    <p>Connected: {{ store.connected }}</p>
    <p>Players: {{ store.players.length }}</p>
  </div>
</template>

<style scoped>
.game-view {
  text-align: center;
  padding: 2rem;
}

code {
  background: #e0d8cc;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}
</style>
