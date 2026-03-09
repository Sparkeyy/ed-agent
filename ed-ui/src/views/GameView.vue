<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import type { ValidAction } from '../types'

import SeasonTracker from '../components/SeasonTracker.vue'
import ResourceDisplay from '../components/ResourceDisplay.vue'
import GameBoard from '../components/GameBoard.vue'
import MeadowDisplay from '../components/MeadowDisplay.vue'
import PlayerCity from '../components/PlayerCity.vue'
import PlayerHand from '../components/PlayerHand.vue'
import ActionBar from '../components/ActionBar.vue'
import EventsPanel from '../components/EventsPanel.vue'
import DebugPanel from '../components/DebugPanel.vue'
import StatsPanel from '../components/StatsPanel.vue'

const route = useRoute()
const router = useRouter()
const store = useGameStore()
const gameId = route.params.id as string

const activeCityTab = ref<string | null>(null)
const debugPanel = ref<InstanceType<typeof DebugPanel> | null>(null)
const statsPanel = ref<InstanceType<typeof StatsPanel> | null>(null)

onMounted(() => {
  if (!store.gameId) {
    store.loadSession(gameId)
  }
  store.connectSSE()
  store.refreshState()
})

onUnmounted(() => {
  store.disconnect()
})

// Computed: derive playable info from validActions
const playableHandCardNames = computed<string[]>(() => {
  return store.validActions
    .filter(a => a.action_type === 'play_card' && a.source === 'hand' && a.card_name)
    .map(a => a.card_name!)
})

const playableMeadowIndices = computed<number[]>(() => {
  return store.validActions
    .filter(a => a.action_type === 'play_card' && a.source === 'meadow' && a.meadow_index !== undefined)
    .map(a => a.meadow_index!)
})

const validLocationIds = computed<string[]>(() => {
  return store.validActions
    .filter(a => a.action_type === 'place_worker' && a.location_id)
    .map(a => a.location_id!)
})

const canPrepareForSeason = computed(() => {
  return store.validActions.some(a => a.action_type === 'prepare_for_season')
})

const claimableEventIds = computed<string[]>(() => {
  // Events would be claim_event actions if the backend supports them
  return []
})

// City tabs: me first, then opponents
const cityTabs = computed(() => {
  const tabs: Array<{ id: string; name: string; isMe: boolean }> = []
  if (store.myPlayer) {
    tabs.push({ id: store.myPlayer.id, name: 'My City', isMe: true })
  }
  for (const opp of store.opponents) {
    tabs.push({ id: opp.id, name: opp.name, isMe: false })
  }
  return tabs
})

const activeCityPlayer = computed(() => {
  const tabId = activeCityTab.value || store.myPlayer?.id
  return store.state?.players.find(p => p.id === tabId)
})

const activeCityIsMe = computed(() => {
  return activeCityPlayer.value?.id === store.myPlayerId
})

// Actions
function captureAndSubmit(action: ValidAction) {
  debugPanel.value?.captureAction(action)
  store.submitAction(action)
}

function handlePlayFromHand(cardName: string) {
  const action = store.validActions.find(
    a => a.action_type === 'play_card' && a.source === 'hand' && a.card_name === cardName
  )
  if (action) captureAndSubmit(action)
}

function handlePlayFromMeadow(index: number) {
  const action = store.validActions.find(
    a => a.action_type === 'play_card' && a.source === 'meadow' && a.meadow_index === index
  )
  if (action) captureAndSubmit(action)
}

function handlePlaceWorker(locationId: string) {
  const action: ValidAction = { action_type: 'place_worker', location_id: locationId }
  captureAndSubmit(action)
}

function handlePrepareForSeason() {
  const action: ValidAction = { action_type: 'prepare_for_season' }
  captureAndSubmit(action)
}

function handleClaimEvent(_eventId: string) {
  // Placeholder for event claiming
}

function copyGameId() {
  navigator.clipboard.writeText(gameId).catch(() => {})
}

function goToScores() {
  router.push(`/scores/${gameId}`)
}
</script>

<template>
  <!-- Waiting Room -->
  <div v-if="store.lobbyState" class="waiting-room">
    <div class="waiting-card">
      <h1 class="waiting-title">The Valley Awaits</h1>
      <p class="waiting-sub">Waiting for players to join...</p>

      <div class="waiting-players">
        <div class="waiting-count">
          {{ store.lobbyState.current_count }} / {{ store.lobbyState.max_players }} players
        </div>
        <div class="player-list">
          <div
            v-for="(name, id) in store.lobbyState.players"
            :key="id"
            class="player-entry"
          >
            <span class="player-dot"></span>
            <span class="player-name">{{ name }}</span>
            <span v-if="id === store.myPlayerId" class="you-badge">you</span>
          </div>
          <div
            v-for="i in (store.lobbyState.max_players - store.lobbyState.current_count)"
            :key="'empty-' + i"
            class="player-entry empty"
          >
            <span class="player-dot empty-dot"></span>
            <span class="player-name empty-name">Waiting...</span>
          </div>
        </div>
      </div>

      <div class="share-section">
        <label class="share-label">Share this Game ID with friends:</label>
        <div class="share-id" @click="copyGameId">
          <code>{{ gameId }}</code>
          <span class="copy-hint">click to copy</span>
        </div>
      </div>

      <div class="waiting-animation">
        <span class="falling-leaf" v-for="i in 5" :key="i" :style="{ animationDelay: (i * 0.8) + 's', left: (10 + i * 18) + '%' }">&#127809;</span>
      </div>
    </div>
  </div>

  <div class="game-layout" v-else-if="store.state">
    <!-- Game Over Overlay -->
    <div v-if="store.gameOver" class="game-over-overlay" @click="goToScores">
      <div class="game-over-card">
        <h2 class="game-over-title">Game Over!</h2>
        <p class="game-over-sub">Click to view scores</p>
      </div>
    </div>

    <!-- Top bar: Season + Turn info + Resources -->
    <div class="top-bar">
      <SeasonTracker
        :season="store.myPlayer?.season ?? 'winter'"
        :turn-number="store.state.turn_number"
      />
      <div class="top-info">
        <div class="deck-info">
          <span class="info-label">Deck</span>
          <span class="info-value">{{ store.state.deck_size }}</span>
        </div>
        <div class="deck-info">
          <span class="info-label">Discard</span>
          <span class="info-value">{{ store.state.discard_size }}</span>
        </div>
      </div>
      <ResourceDisplay
        v-if="store.myPlayer"
        :resources="store.myPlayer.resources"
        :compact="true"
      />
    </div>

    <!-- Middle: Board + Meadow + Events -->
    <div class="middle-area">
      <div class="board-column">
        <GameBoard
          :basic-locations="store.state.basic_locations"
          :forest-locations="store.state.forest_locations"
          :valid-location-ids="validLocationIds"
          @place-worker="handlePlaceWorker"
        />
      </div>
      <div class="meadow-column">
        <MeadowDisplay
          :meadow="store.meadow"
          :playable-indices="playableMeadowIndices"
          @play-from-meadow="handlePlayFromMeadow"
        />
        <EventsPanel
          v-if="store.state.events"
          :events="store.state.events"
          :claimable-event-ids="claimableEventIds"
          @claim-event="handleClaimEvent"
        />
      </div>
    </div>

    <!-- City tabs -->
    <div class="city-section">
      <div class="city-tabs">
        <button
          v-for="tab in cityTabs"
          :key="tab.id"
          class="city-tab"
          :class="{ active: (activeCityTab || store.myPlayer?.id) === tab.id }"
          @click="activeCityTab = tab.id"
        >
          {{ tab.name }}
        </button>
      </div>
      <PlayerCity
        v-if="activeCityPlayer"
        :player="activeCityPlayer"
        :is-me="activeCityIsMe"
      />
    </div>

    <!-- Hand -->
    <PlayerHand
      v-if="store.myPlayer?.hand"
      :hand="store.myPlayer.hand"
      :playable-card-names="playableHandCardNames"
      @play-from-hand="handlePlayFromHand"
    />

    <!-- Action bar -->
    <ActionBar
      :is-my-turn="store.isMyTurn"
      :can-prepare-for-season="canPrepareForSeason"
      :game-over="store.gameOver"
      :current-player-name="store.currentPlayer?.name"
      @prepare-for-season="handlePrepareForSeason"
    />

    <!-- Overlay panels -->
    <DebugPanel ref="debugPanel" />
    <StatsPanel ref="statsPanel" />

    <!-- Error toast -->
    <div v-if="store.error" class="error-toast">
      {{ store.error }}
    </div>
  </div>

  <!-- Loading state -->
  <div v-else class="loading-state">
    <div class="loading-spinner"></div>
    <p>Entering the valley...</p>
  </div>
</template>

<style scoped>
.game-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: var(--parchment);
  position: relative;
}

/* Top bar */
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--gap-sm) var(--gap-md);
  background: var(--parchment-dark);
  border-bottom: 1px solid var(--parchment-deep);
  flex-shrink: 0;
  gap: var(--gap-md);
}

.top-info {
  display: flex;
  gap: var(--gap-md);
}

.deck-info {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.info-label {
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--ink-faint);
}

.info-value {
  font-weight: 700;
  font-size: 1rem;
  color: var(--ink);
}

/* Middle area */
.middle-area {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.board-column {
  flex: 1;
  overflow-y: auto;
  border-right: 1px solid var(--parchment-deep);
}

.meadow-column {
  width: 340px;
  flex-shrink: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

/* City section */
.city-section {
  border-top: 1px solid var(--parchment-deep);
  max-height: 180px;
  overflow-y: auto;
  flex-shrink: 0;
}

.city-tabs {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--parchment-deep);
  background: var(--parchment-dark);
}

.city-tab {
  padding: var(--gap-xs) var(--gap-md);
  font-family: var(--font-display);
  font-size: 0.78rem;
  color: var(--ink-faint);
  border: none;
  background: none;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: color 0.2s ease, border-color 0.2s ease;
}

.city-tab:hover {
  color: var(--ink);
}

.city-tab.active {
  color: var(--forest-light);
  border-bottom-color: var(--forest-light);
}

/* Game over overlay */
.game-over-overlay {
  position: absolute;
  inset: 0;
  background: rgba(26, 47, 26, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  cursor: pointer;
  animation: fadeIn 0.5s ease;
}

.game-over-card {
  background: var(--parchment);
  padding: var(--gap-xl);
  border-radius: var(--radius-lg);
  text-align: center;
  box-shadow: var(--shadow-lg);
}

.game-over-title {
  font-family: var(--font-display);
  font-size: 2.5rem;
  color: var(--forest-dark);
  margin-bottom: var(--gap-sm);
}

.game-over-sub {
  color: var(--ink-faint);
  font-style: italic;
}

/* Error toast */
.error-toast {
  position: absolute;
  bottom: 60px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--red-destination);
  color: white;
  padding: var(--gap-sm) var(--gap-lg);
  border-radius: var(--radius-md);
  font-size: 0.85rem;
  box-shadow: var(--shadow-md);
  animation: slideUp 0.3s ease;
  z-index: 50;
}

/* Loading */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100vh;
  gap: var(--gap-md);
  color: var(--ink-faint);
  font-family: var(--font-display);
  font-size: 1.1rem;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--parchment-deep);
  border-top-color: var(--forest-light);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Waiting Room */
.waiting-room {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: var(--parchment);
  position: relative;
  overflow: hidden;
}

.waiting-card {
  background: white;
  border: var(--border-card);
  border-radius: var(--radius-lg);
  padding: var(--gap-xl) var(--gap-xl) var(--gap-lg);
  box-shadow: var(--shadow-lg);
  max-width: 440px;
  width: 90%;
  text-align: center;
  animation: fadeIn 0.5s ease;
  position: relative;
  z-index: 1;
}

.waiting-title {
  font-family: var(--font-display);
  font-size: 2rem;
  color: var(--forest-dark);
  margin-bottom: var(--gap-xs);
}

.waiting-sub {
  font-family: var(--font-body);
  font-style: italic;
  color: var(--ink-faint);
  margin-bottom: var(--gap-lg);
}

.waiting-players {
  margin-bottom: var(--gap-lg);
}

.waiting-count {
  font-family: var(--font-display);
  font-size: 0.85rem;
  color: var(--ink-faint);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: var(--gap-sm);
}

.player-list {
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
}

.player-entry {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  padding: var(--gap-sm) var(--gap-md);
  background: var(--parchment);
  border-radius: var(--radius-md);
  border: 1px solid var(--parchment-deep);
}

.player-entry.empty {
  opacity: 0.4;
  border-style: dashed;
}

.player-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--forest-glow);
  flex-shrink: 0;
}

.empty-dot {
  background: var(--parchment-deep);
}

.player-name {
  font-family: var(--font-card);
  font-size: 1rem;
  color: var(--ink);
}

.empty-name {
  color: var(--ink-faint);
  font-style: italic;
}

.you-badge {
  margin-left: auto;
  font-size: 0.7rem;
  font-family: var(--font-display);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--forest-light);
  background: var(--green-production-bg);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

.share-section {
  margin-top: var(--gap-md);
}

.share-label {
  display: block;
  font-size: 0.78rem;
  color: var(--ink-faint);
  margin-bottom: var(--gap-xs);
}

.share-id {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--gap-sm);
  padding: var(--gap-sm) var(--gap-md);
  background: var(--parchment);
  border: 1px solid var(--parchment-deep);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.share-id:hover {
  border-color: var(--gold);
  box-shadow: var(--shadow-glow);
}

.share-id code {
  font-family: monospace;
  font-size: 0.9rem;
  color: var(--ink);
  word-break: break-all;
}

.copy-hint {
  font-size: 0.65rem;
  color: var(--ink-faint);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  flex-shrink: 0;
}

.waiting-animation {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  z-index: 0;
}

.falling-leaf {
  position: absolute;
  top: -30px;
  font-size: 1.2rem;
  opacity: 0.3;
  animation: leaf-fall 6s linear infinite;
}
</style>
