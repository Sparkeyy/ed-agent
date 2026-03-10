<script setup lang="ts">

defineProps<{
  isMyTurn: boolean
  canPrepareForSeason: boolean
  gameOver: boolean
  currentPlayerName?: string
}>()

const emit = defineEmits<{
  'prepare-for-season': []
  'pass': []
}>()
</script>

<template>
  <div class="action-bar" :class="{ 'my-turn': isMyTurn, 'game-over': gameOver }">
    <div v-if="gameOver" class="turn-status">
      Game Over
    </div>
    <template v-else>
      <div class="turn-status">
        <template v-if="isMyTurn">
          <span class="your-turn-text">Your turn!</span>
        </template>
        <template v-else>
          <span class="waiting-text">Waiting for {{ currentPlayerName || '...' }}</span>
        </template>
      </div>
      <div v-if="isMyTurn" class="action-buttons">
        <button
          v-if="canPrepareForSeason"
          class="btn btn-season"
          @click="emit('prepare-for-season')"
        >
          Prepare for Season
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--gap-sm) var(--gap-lg);
  background: var(--parchment-dark);
  border-top: 1.5px solid var(--parchment-deep);
  min-height: 48px;
}

.action-bar.my-turn {
  background: linear-gradient(to right, var(--parchment-dark), rgba(201, 169, 110, 0.15));
  border-top: 2px solid var(--gold);
  animation: pulse-glow 3s ease-in-out infinite;
}

.action-bar.game-over {
  background: var(--forest-dark);
  color: var(--parchment);
}

.turn-status {
  font-family: var(--font-display);
  font-size: 0.95rem;
}

.your-turn-text {
  color: var(--forest-light);
  font-weight: 700;
  font-size: 1.05rem;
}

.waiting-text {
  color: var(--ink-faint);
  font-style: italic;
}

.action-buttons {
  display: flex;
  gap: var(--gap-sm);
}

.btn {
  padding: 6px 16px;
  font-family: var(--font-body);
  font-size: 0.85rem;
  font-weight: 600;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 0.2s ease, transform 0.15s ease;
}

.btn:active {
  transform: scale(0.97);
}

.btn-season {
  background: var(--forest-light);
  color: white;
  padding: 8px 24px;
  font-size: 0.9rem;
  font-family: var(--font-display);
  letter-spacing: 0.03em;
}

.btn-season:hover {
  background: var(--forest-mid);
}
</style>
