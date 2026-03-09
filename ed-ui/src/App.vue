<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const isGameView = computed(() => route.name === 'Game')
</script>

<template>
  <div id="everdell-app">
    <header v-if="!isGameView" class="app-header">
      <div class="header-inner">
        <router-link to="/" class="logo-link">
          <h1 class="app-title">Everdell</h1>
        </router-link>
        <nav class="app-nav">
          <router-link to="/">Lobby</router-link>
          <router-link to="/leaderboard">Leaderboard</router-link>
        </nav>
      </div>
    </header>
    <main :class="{ 'game-fullscreen': isGameView }">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
#everdell-app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background: var(--forest-dark);
  border-bottom: 2px solid var(--forest-mid);
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 2rem;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.logo-link {
  text-decoration: none;
}

.app-title {
  font-family: var(--font-display);
  font-size: 1.5rem;
  color: var(--gold-bright);
  letter-spacing: 0.06em;
}

.app-nav {
  display: flex;
  gap: 1.5rem;
}

.app-nav a {
  color: var(--parchment);
  text-decoration: none;
  font-family: var(--font-body);
  font-size: 0.9rem;
  opacity: 0.8;
  transition: opacity 0.2s ease;
}

.app-nav a:hover,
.app-nav a.router-link-active {
  opacity: 1;
  text-decoration: underline;
  text-underline-offset: 4px;
}

main {
  flex: 1;
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

main.game-fullscreen {
  padding: 0;
  max-width: none;
}
</style>
