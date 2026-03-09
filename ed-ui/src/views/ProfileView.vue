<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
const playerId = route.params.id as string
</script>

<template>
  <div class="profile-view">
    <h2>Player Profile</h2>
    <p>Player ID: <code>{{ playerId }}</code></p>
    <p>Player stats and history will be displayed here.</p>
  </div>
</template>

<style scoped>
.profile-view {
  text-align: center;
  padding: 2rem;
}

code {
  background: #e0d8cc;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}
</style>
