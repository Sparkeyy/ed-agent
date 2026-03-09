<script setup lang="ts">
</script>

<template>
  <div id="everdell-app">
    <header>
      <h1>Everdell</h1>
      <nav>
        <router-link to="/">Lobby</router-link>
        <router-link to="/leaderboard">Leaderboard</router-link>
      </nav>
    </header>
    <main>
      <router-view />
    </main>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: system-ui, -apple-system, sans-serif;
  background: #f5f0e8;
  color: #2c1810;
}

#everdell-app {
  min-height: 100vh;
}

header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 2rem;
  background: #3a5a40;
  color: #f5f0e8;
}

header h1 {
  font-size: 1.5rem;
}

nav a {
  color: #f5f0e8;
  text-decoration: none;
  margin-left: 1.5rem;
}

nav a:hover {
  text-decoration: underline;
}

main {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}
</style>
