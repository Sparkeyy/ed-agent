<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGameStore } from '../stores/game'
import { addAiPlayer } from '../api/client'
import type { ValidAction, ResourceBank } from '../types'

import CardComponent from '../components/CardComponent.vue'
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
import CardInfoModal from '../components/CardInfoModal.vue'
import HelpPanel from '../components/HelpPanel.vue'
import ChoicePanel from '../components/ChoicePanel.vue'
import { CARD_INFO, LOCATION_INFO } from '../data/card-info'
import { EVENT_IMAGES, FOREST_IMAGES } from '../data/card-images'

const route = useRoute()
const router = useRouter()
const store = useGameStore()
const gameId = route.params.id as string

const activeCityTab = ref<string | null>(null)
const debugPanel = ref<InstanceType<typeof DebugPanel> | null>(null)
const statsPanel = ref<InstanceType<typeof StatsPanel> | null>(null)
const aiDifficulty = ref<'apprentice' | 'journeyman' | 'master'>('journeyman')
const addingAi = ref(false)
const aiError = ref('')
const aiNameIndex = ref(0)
const AI_NAMES = ['Rugwort', 'Bramblewick', 'Thistledew', 'Mossclaw', 'Fernwhisper', 'Ashenbark']
const discardMode = ref(false)
const selectedDiscards = ref<string[]>([])
const discardTarget = ref<{ locationId: string; required: number } | null>(null)

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
  return store.validActions
    .filter(a => a.action_type === 'claim_event' && a.event_id)
    .map(a => a.event_id!)
})

// Pending choice (e.g., Undertaker meadow selection, Storehouse resource pick)
const pendingChoice = computed(() => store.state?.pending_choice ?? null)

// Options-based choice (new generic system) vs meadow-based (legacy Undertaker)
const isOptionsPendingChoice = computed(() => {
  return pendingChoice.value?.options && pendingChoice.value.options.length > 0
})

const pendingChoiceMeadowIndices = computed<number[]>(() => {
  if (!pendingChoice.value || isOptionsPendingChoice.value) return []
  return store.validActions
    .filter(a => a.action_type === 'resolve_choice' && a.meadow_index !== undefined)
    .map(a => a.meadow_index!)
})

const workerDisplay = computed(() => {
  if (!store.myPlayer) return null
  const available = store.myPlayer.workers_total - store.myPlayer.workers_placed
  return { available, total: store.myPlayer.workers_total }
})

const leftForest = computed(() => {
  const all = store.state?.forest_locations || []
  const mid = Math.ceil(all.length / 2)
  return all.slice(0, mid)
})

const rightForest = computed(() => {
  const all = store.state?.forest_locations || []
  const mid = Math.ceil(all.length / 2)
  return all.slice(mid)
})

const playerNamesMap = computed<Record<string, string>>(() => {
  const map: Record<string, string> = {}
  if (store.state) {
    for (const p of store.state.players) {
      map[p.id] = p.name
    }
  }
  return map
})

const playerOrderList = computed<string[]>(() => {
  if (!store.state) return []
  return store.state.players.map(p => p.id)
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
  const actions = store.validActions.filter(
    a => a.action_type === 'play_card' && a.source === 'hand' && a.card_name === cardName
  )
  const action = actions.find(a => a.use_paired_construction) || actions[0]
  if (action) captureAndSubmit(action)
}

function handlePlayFromMeadow(index: number) {
  const actions = store.validActions.filter(
    a => a.action_type === 'play_card' && a.source === 'meadow' && a.meadow_index === index
  )
  const action = actions.find(a => a.use_paired_construction) || actions[0]
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

function handleClaimEvent(eventId: string) {
  const action: ValidAction = { action_type: 'claim_event', event_id: eventId }
  captureAndSubmit(action)
}

function handleResolveChoice(meadowIndex: number) {
  const action = store.validActions.find(
    a => a.action_type === 'resolve_choice' && a.meadow_index === meadowIndex
  )
  if (action) captureAndSubmit(action)
}

function handleChoicePanelSelect(choiceIndex: number) {
  const action = store.validActions.find(
    a => a.action_type === 'resolve_choice' && a.choice_index === choiceIndex
  )
  if (action) captureAndSubmit(action)
}

function toggleDiscardCard(cardName: string) {
  const idx = selectedDiscards.value.indexOf(cardName)
  if (idx >= 0) {
    selectedDiscards.value.splice(idx, 1)
  } else {
    selectedDiscards.value.push(cardName)
  }
}

function confirmDiscard() {
  if (!discardTarget.value) return
  const action: ValidAction = {
    action_type: 'place_worker',
    location_id: discardTarget.value.locationId,
    discard_cards: [...selectedDiscards.value],
  }
  captureAndSubmit(action)
  discardMode.value = false
  selectedDiscards.value = []
  discardTarget.value = null
}

function cancelDiscard() {
  discardMode.value = false
  selectedDiscards.value = []
  discardTarget.value = null
}

function copyGameId() {
  navigator.clipboard.writeText(gameId).catch(() => {})
}

async function handleAddAi() {
  addingAi.value = true
  aiError.value = ''
  try {
    const name = AI_NAMES[aiNameIndex.value % AI_NAMES.length]
    aiNameIndex.value++
    await addAiPlayer(gameId, aiDifficulty.value, name)
  } catch (e: any) {
    aiError.value = e.message ?? 'Failed to add AI player'
  } finally {
    addingAi.value = false
  }
}

function goToScores() {
  router.push(`/scores/${gameId}`)
}

// Info modal state
const infoModal = ref({
  visible: false,
  title: '',
  subtitle: '',
  cardType: '',
  category: '',
  description: '',
  ability: '',
  cost: undefined as ResourceBank | undefined,
  points: undefined as number | undefined,
  imageUrl: null as string | null,
})

function handleCardInfo(cardName: string) {
  const info = CARD_INFO[cardName]
  // Find card data from meadow, hand, or any player's city
  let cardData: any = null
  if (store.state) {
    cardData = store.state.meadow.find(c => c.name === cardName)
    if (!cardData && store.myPlayer?.hand) {
      cardData = store.myPlayer.hand.find(c => c.name === cardName)
    }
    if (!cardData) {
      for (const p of store.state.players) {
        cardData = p.city.find(c => c.name === cardName)
        if (cardData) break
      }
    }
  }
  infoModal.value = {
    visible: true,
    title: cardName,
    subtitle: cardData ? `${cardData.unique ? 'Unique' : 'Common'} ${cardData.category}` : '',
    cardType: cardData?.card_type || '',
    category: cardData?.category || '',
    description: info?.description || '',
    ability: info?.ability || 'No ability info available.',
    cost: cardData?.cost,
    points: cardData?.base_points,
    imageUrl: null,
  }
}

function handleLocationInfo(locationId: string) {
  const reward = LOCATION_INFO[locationId]
  infoModal.value = {
    visible: true,
    title: locationId.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    subtitle: 'Location',
    cardType: '',
    category: '',
    description: '',
    ability: reward || 'No info available for this location.',
    cost: undefined,
    points: undefined,
    imageUrl: FOREST_IMAGES[locationId] || null,
  }
}

function handleEventInfo(eventData: { name: string; description?: string; required_cards?: string[]; points: number }) {
  const reqText = eventData.required_cards?.length
    ? `Requires: ${eventData.required_cards.join(' + ')}`
    : ''
  // Combine description and requirements so both always show
  const descParts = [eventData.description, reqText].filter(Boolean)
  infoModal.value = {
    visible: true,
    title: eventData.name,
    subtitle: 'Event',
    cardType: '',
    category: '',
    description: '',
    ability: descParts.join('\n\n') || 'No details available for this event.',
    cost: undefined,
    points: eventData.points,
    imageUrl: EVENT_IMAGES[eventData.name] || null,
  }
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

      <div class="ai-section" v-if="store.lobbyState && store.lobbyState.current_count < store.lobbyState.max_players">
        <div class="ai-divider">
          <span class="ai-divider-line"></span>
          <span class="ai-divider-text">or</span>
          <span class="ai-divider-line"></span>
        </div>
        <p class="ai-label">Add AI Opponents</p>
        <div class="ai-controls">
          <select v-model="aiDifficulty" class="ai-select">
            <option value="apprentice">Apprentice</option>
            <option value="journeyman">Journeyman</option>
            <option value="master">Master</option>
          </select>
          <button class="ai-btn" @click="handleAddAi" :disabled="addingAi">
            <span v-if="addingAi">Adding...</span>
            <span v-else>+ Add AI</span>
          </button>
        </div>
        <p class="ai-hint">You can add multiple AI players with different difficulty levels</p>
        <p v-if="aiError" class="ai-error">{{ aiError }}</p>
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
        <div class="deck-info" v-if="workerDisplay">
          <span class="info-label">Workers</span>
          <span class="info-value">{{ workerDisplay.available }}/{{ workerDisplay.total }}</span>
        </div>
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

    <!-- Player worker indicators -->
    <div class="player-workers-bar">
      <div
        v-for="p in store.state.players"
        :key="'w-' + p.id"
        class="player-worker-indicator"
        :class="{ 'is-current': p.id === store.state.current_player_id }"
      >
        <span class="pw-name">{{ p.name }}</span>
        <span class="pw-workers">{{ p.workers_total - p.workers_placed }}/{{ p.workers_total }}</span>
        <span class="pw-season">{{ p.season }}</span>
      </div>
    </div>

    <!-- Board area: single column flow -->
    <div class="board-area">
      <!-- Events at top -->
      <EventsPanel
        v-if="store.state.events"
        :events="store.state.events"
        :claimable-event-ids="claimableEventIds"
        @claim-event="handleClaimEvent"
        @event-info="handleEventInfo"
      />

      <!-- Basic Locations — single horizontal row -->
      <GameBoard
        :basic-locations="store.state.basic_locations"
        :forest-locations="[]"
        :haven-locations="[]"
        :journey-locations="[]"
        :valid-location-ids="validLocationIds"
        :player-names="playerNamesMap"
        :player-order="playerOrderList"
        :current-season="store.myPlayer?.season ?? 'winter'"
        @place-worker="handlePlaceWorker"
        @location-info="handleLocationInfo"
      />

      <!-- Forest Left | Meadow 4x2 | Forest Right -->
      <div class="forest-meadow-row">
        <GameBoard
          :basic-locations="[]"
          :forest-locations="leftForest"
          :haven-locations="[]"
          :journey-locations="[]"
          :valid-location-ids="validLocationIds"
          :player-names="playerNamesMap"
        :player-order="playerOrderList"
          :current-season="store.myPlayer?.season ?? 'winter'"
          @place-worker="handlePlaceWorker"
          @location-info="handleLocationInfo"
        />
        <div class="meadow-wrapper">
          <!-- Options-based choice panel (Storehouse, Courthouse, etc.) -->
          <ChoicePanel
            v-if="pendingChoice && isOptionsPendingChoice"
            :pending-choice="pendingChoice"
            @choose="handleChoicePanelSelect"
          />
          <!-- Legacy meadow choice banner (Undertaker) -->
          <div v-else-if="pendingChoice" class="pending-choice-banner">
            <span class="pending-choice-icon">&#9881;</span>
            <span class="pending-choice-text">{{ pendingChoice.prompt }}</span>
          </div>
          <MeadowDisplay
            :meadow="store.meadow"
            :playable-indices="pendingChoice && !isOptionsPendingChoice ? pendingChoiceMeadowIndices : playableMeadowIndices"
            @play-from-meadow="pendingChoice && !isOptionsPendingChoice ? handleResolveChoice($event) : handlePlayFromMeadow($event)"
            @card-info="handleCardInfo"
          />
        </div>
        <GameBoard
          :basic-locations="[]"
          :forest-locations="rightForest"
          :haven-locations="[]"
          :journey-locations="[]"
          :valid-location-ids="validLocationIds"
          :player-names="playerNamesMap"
        :player-order="playerOrderList"
          :current-season="store.myPlayer?.season ?? 'winter'"
          @place-worker="handlePlaceWorker"
          @location-info="handleLocationInfo"
        />
      </div>

      <!-- Journey (left) + Haven (right) -->
      <div class="haven-journey-row">
        <GameBoard
          :basic-locations="[]"
          :forest-locations="[]"
          :haven-locations="[]"
          :journey-locations="store.state.journey_locations || []"
          :valid-location-ids="validLocationIds"
          :player-names="playerNamesMap"
        :player-order="playerOrderList"
          :current-season="store.myPlayer?.season ?? 'winter'"
          @place-worker="handlePlaceWorker"
          @location-info="handleLocationInfo"
        />
        <GameBoard
          :basic-locations="[]"
          :forest-locations="[]"
          :haven-locations="store.state.haven_locations || []"
          :journey-locations="[]"
          :valid-location-ids="validLocationIds"
          :player-names="playerNamesMap"
        :player-order="playerOrderList"
          :current-season="store.myPlayer?.season ?? 'winter'"
          @place-worker="handlePlaceWorker"
          @location-info="handleLocationInfo"
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
        :game-id="gameId"
        @card-info="handleCardInfo"
      />
    </div>

    <!-- Hand -->
    <PlayerHand
      v-if="store.myPlayer?.hand && !discardMode"
      :hand="store.myPlayer.hand"
      :playable-card-names="playableHandCardNames"
      @play-from-hand="handlePlayFromHand"
      @card-info="handleCardInfo"
    />

    <!-- Discard Selection Mode -->
    <div v-if="discardMode && store.myPlayer?.hand" class="discard-panel">
      <div class="discard-header">
        <span class="discard-title">Select {{ discardTarget?.required }} card(s) to discard</span>
        <span class="discard-count">{{ selectedDiscards.length }} / {{ discardTarget?.required }}</span>
      </div>
      <div class="discard-hand">
        <div
          v-for="(card, index) in store.myPlayer.hand"
          :key="card.name + '-' + index"
          class="discard-card-wrapper"
          :class="{ 'discard-selected': selectedDiscards.includes(card.name) }"
          @click="toggleDiscardCard(card.name)"
        >
          <CardComponent :card="card" :selected="selectedDiscards.includes(card.name)" />
        </div>
      </div>
      <div class="discard-actions">
        <button class="discard-btn cancel" @click="cancelDiscard">Cancel</button>
        <button
          class="discard-btn confirm"
          :disabled="selectedDiscards.length !== discardTarget?.required"
          @click="confirmDiscard"
        >Confirm Discard</button>
      </div>
    </div>

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
    <HelpPanel />

    <!-- Info Modal -->
    <CardInfoModal
      :visible="infoModal.visible"
      :title="infoModal.title"
      :subtitle="infoModal.subtitle"
      :card-type="infoModal.cardType"
      :category="infoModal.category"
      :description="infoModal.description"
      :ability="infoModal.ability"
      :cost="infoModal.cost"
      :points="infoModal.points"
      :image-url="infoModal.imageUrl"
      @close="infoModal.visible = false"
    />

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

/* Player workers bar */
.player-workers-bar {
  display: flex;
  gap: var(--gap-sm);
  padding: var(--gap-xs) var(--gap-md);
  background: var(--parchment);
  border-bottom: 1px solid var(--parchment-deep);
  flex-shrink: 0;
  justify-content: center;
  flex-wrap: wrap;
}

.player-worker-indicator {
  display: flex;
  align-items: center;
  gap: var(--gap-xs);
  padding: 3px 10px;
  background: var(--parchment-dark);
  border-radius: var(--radius-md);
  border: 1.5px solid var(--parchment-deep);
  font-size: 0.75rem;
}

.player-worker-indicator.is-current {
  border-color: var(--gold);
  background: rgba(201, 169, 110, 0.1);
}

.pw-name {
  font-family: var(--font-card);
  font-weight: 600;
  color: var(--ink);
}

.pw-workers {
  font-weight: 700;
  color: var(--forest-light);
}

.pw-season {
  font-size: 0.65rem;
  color: var(--ink-faint);
  text-transform: capitalize;
}

/* Board area: single-column flow */
.board-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: clamp(4px, 0.5vw, 8px);
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: clamp(4px, 0.5vw, 8px);
}

.forest-meadow-row {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: clamp(4px, 0.5vw, 8px);
  width: 100%;
  align-items: start;
}

.haven-journey-row {
  display: flex;
  justify-content: space-between;
  width: 100%;
  gap: var(--gap-md);
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

/* AI opponent section */
.ai-section {
  margin-top: var(--gap-md);
}

.ai-divider {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  margin-bottom: var(--gap-md);
}

.ai-divider-line {
  flex: 1;
  height: 1px;
  background: var(--parchment-deep);
}

.ai-divider-text {
  font-size: 0.75rem;
  color: var(--ink-faint);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.ai-label {
  font-family: var(--font-display);
  font-size: 0.85rem;
  color: var(--ink-light);
  margin-bottom: var(--gap-sm);
}

.ai-controls {
  display: flex;
  gap: var(--gap-sm);
}

.ai-select {
  flex: 1;
  padding: 8px 12px;
  border: 1.5px solid var(--parchment-deep);
  border-radius: var(--radius-md);
  background: var(--parchment);
  font-family: var(--font-body);
  font-size: 0.9rem;
  color: var(--ink);
  cursor: pointer;
}

.ai-select:focus {
  outline: none;
  border-color: var(--gold);
}

.ai-btn {
  padding: 8px 20px;
  background: var(--purple-prosperity);
  color: white;
  font-family: var(--font-display);
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background 0.2s ease, transform 0.15s ease;
  white-space: nowrap;
}

.ai-btn:hover:not(:disabled) {
  background: var(--forest-mid);
}

.ai-btn:active:not(:disabled) {
  transform: scale(0.97);
}

.ai-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ai-hint {
  margin-top: var(--gap-xs);
  font-size: 0.72rem;
  color: var(--ink-faint);
  font-style: italic;
}

.ai-error {
  margin-top: var(--gap-xs);
  font-size: 0.8rem;
  color: var(--red-destination);
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

/* Discard panel */
.discard-panel {
  padding: var(--gap-sm) var(--gap-md);
  background: rgba(168, 56, 50, 0.05);
  border-top: 2px solid var(--red-destination, #a83832);
}

.discard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--gap-sm);
}

.discard-title {
  font-family: var(--font-display);
  font-size: 0.9rem;
  color: var(--red-destination, #a83832);
}

.discard-count {
  font-size: 0.8rem;
  color: var(--ink-faint);
  font-weight: 600;
}

.discard-hand {
  display: flex;
  gap: var(--gap-sm);
  overflow-x: auto;
  padding-bottom: var(--gap-sm);
}

.discard-card-wrapper {
  cursor: pointer;
  transition: transform 0.15s ease;
}

.discard-card-wrapper:hover {
  transform: translateY(-2px);
}

.discard-card-wrapper.discard-selected {
  transform: translateY(-4px);
}

.discard-actions {
  display: flex;
  gap: var(--gap-sm);
  justify-content: flex-end;
}

.discard-btn {
  padding: 6px 16px;
  border: none;
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
}

.discard-btn.cancel {
  background: var(--parchment-deep);
  color: var(--ink-light);
}

.discard-btn.confirm {
  background: var(--red-destination, #a83832);
  color: white;
}

.discard-btn.confirm:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Pending choice banner */
.meadow-wrapper {
  display: flex;
  flex-direction: column;
  align-items: stretch;
}

.pending-choice-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--gap-sm);
  padding: 6px 12px;
  background: rgba(201, 169, 110, 0.15);
  border: 1.5px solid var(--gold);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
  animation: pulse-glow 2s ease-in-out infinite;
}

.pending-choice-icon {
  font-size: 0.9rem;
}

.pending-choice-text {
  font-family: var(--font-display);
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--ink);
}
</style>
