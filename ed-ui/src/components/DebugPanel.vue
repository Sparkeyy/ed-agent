<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useGameStore } from '../stores/game'
import * as api from '../api/client'
import type { MoveEvaluation, MoveQuality, ValidAction } from '../types'

interface AiSuggestion {
  action: any
  reasoning: string
  source: string
}
type Difficulty = 'apprentice' | 'journeyman' | 'master'

const store = useGameStore()
const visible = ref(false)
const loading = ref(false)
const evaluation = ref<MoveEvaluation | null>(null)
const error = ref<string | null>(null)

// Debug mode
const isDebug = computed(() => store.myPlayer?.name?.toLowerCase() === 'debug')
const aiSuggestions = ref<Record<Difficulty, AiSuggestion | null>>({
  apprentice: null,
  journeyman: null,
  master: null,
})
const aiLoading = ref(false)

// Track the last action for evaluation
let lastState: any = null
let lastAction: ValidAction | null = null
let lastValidActions: ValidAction[] = []

const qualityConfig: Record<MoveQuality, { label: string; cssClass: string }> = {
  brilliant: { label: 'Brilliant', cssClass: 'quality-brilliant' },
  good: { label: 'Good', cssClass: 'quality-good' },
  inaccuracy: { label: 'Inaccuracy', cssClass: 'quality-inaccuracy' },
  mistake: { label: 'Mistake', cssClass: 'quality-mistake' },
  blunder: { label: 'Blunder', cssClass: 'quality-blunder' },
}

function toggle() {
  visible.value = !visible.value
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === '`' && !e.ctrlKey && !e.metaKey && !e.altKey) {
    const tag = (e.target as HTMLElement)?.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
    e.preventDefault()
    toggle()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

function describeAction(action: ValidAction | Record<string, any>): string {
  if (!action || typeof action !== 'object') return 'Unknown action'
  if (action.action_type === 'place_worker' && action.location_id) {
    return `Place worker at ${action.location_id}`
  }
  if (action.action_type === 'play_card' && action.card_name) {
    const src = action.source === 'meadow' ? 'meadow' : 'hand'
    return `Play ${action.card_name} from ${src}`
  }
  if (action.action_type === 'prepare_for_season') {
    return 'Prepare for season'
  }
  if (action.action_type === 'claim_event' && action.event_id) {
    return `Claim event ${action.event_id}`
  }
  return action.action_type || JSON.stringify(action).substring(0, 60)
}

// Watch for turn changes — when it stops being my turn, evaluate the last action
watch(
  () => store.state?.turn_number,
  async (newTurn, oldTurn) => {
    if (newTurn === undefined || oldTurn === undefined) return
    if (newTurn <= oldTurn) return
    if (!lastAction || !lastState) return

    loading.value = true
    error.value = null
    try {
      evaluation.value = await api.evaluateMove(lastState, lastAction, lastValidActions)
    } catch (e: any) {
      error.value = e.message ?? 'Failed to evaluate move'
      evaluation.value = null
    } finally {
      loading.value = false
    }
  },
)

// Fetch AI suggestions when it becomes debug player's turn
watch(
  [() => store.isMyTurn, () => store.state?.turn_number],
  async ([myTurn]) => {
    if (!myTurn || !isDebug.value || !store.state) return
    aiLoading.value = true
    aiSuggestions.value = { apprentice: null, journeyman: null, master: null }
    const difficulties: Difficulty[] = ['apprentice', 'journeyman', 'master']
    const promises = difficulties.map(async (d) => {
      try {
        const result = await api.thinkAi(store.state!, store.validActions, d)
        aiSuggestions.value[d] = result
      } catch {
        aiSuggestions.value[d] = { action: {}, reasoning: 'Failed to get suggestion', source: 'error' }
      }
    })
    await Promise.all(promises)
    aiLoading.value = false
  },
)

// Capture pre-action state when it becomes our turn
watch(
  () => store.isMyTurn,
  (isMyTurn) => {
    if (isMyTurn && store.state) {
      // Capture pre-action state when it becomes our turn
      lastState = JSON.parse(JSON.stringify(store.state))
      lastValidActions = [...store.validActions]
    }
  },
  { immediate: true },
)

// Expose a method for GameView to call before submitting
function captureAction(action: ValidAction) {
  lastAction = action
  if (store.state) {
    lastState = JSON.parse(JSON.stringify(store.state))
    lastValidActions = [...store.validActions]
  }
}

defineExpose({ toggle, captureAction })
</script>

<template>
  <div class="debug-toggle-btn" @click="toggle" title="Debug Panel (`)">
    <span class="debug-icon">&#x2699;</span>
  </div>

  <Transition name="slide-right">
    <div v-if="visible" class="debug-panel">
      <div class="debug-header">
        <h3 class="debug-title">Move Analysis</h3>
        <button class="debug-close" @click="toggle">&times;</button>
      </div>

      <div class="debug-body">
        <div v-if="loading" class="debug-loading">
          <div class="debug-spinner"></div>
          <span>Analyzing move...</span>
        </div>

        <div v-else-if="error" class="debug-error">
          {{ error }}
        </div>

        <div v-else-if="evaluation" class="debug-evaluation">
          <div class="quality-badge" :class="qualityConfig[evaluation.quality].cssClass">
            {{ qualityConfig[evaluation.quality].label }}
          </div>

          <p class="eval-explanation">{{ evaluation.explanation }}</p>

          <div v-if="evaluation.alternatives.length > 0" class="eval-alternatives">
            <h4 class="alt-heading">Better alternatives</h4>
            <div
              v-for="(alt, i) in evaluation.alternatives"
              :key="i"
              class="alt-item"
            >
              <div class="alt-action">{{ describeAction(alt.action) }}</div>
              <div class="alt-desc">{{ alt.reason }}</div>
              <div class="alt-delta" :class="{ positive: alt.score_delta > 0 }">
                {{ alt.score_delta > 0 ? '+' : '' }}{{ alt.score_delta.toFixed(1) }}
              </div>
            </div>
          </div>
        </div>

        <!-- AI Suggestions (debug mode) -->
        <div v-if="isDebug && store.isMyTurn" class="ai-suggestions">
          <h4 class="suggestions-heading">AI Suggestions</h4>
          <div v-if="aiLoading" class="debug-loading">
            <div class="debug-spinner"></div>
            <span>Getting AI suggestions...</span>
          </div>
          <div v-else class="suggestion-cards">
            <div v-for="diff in (['apprentice', 'journeyman', 'master'] as Difficulty[])" :key="diff" class="suggestion-card">
              <div class="suggestion-diff" :class="`diff-${diff}`">{{ diff }}</div>
              <template v-if="aiSuggestions[diff]">
                <div class="suggestion-action">{{ describeAction(aiSuggestions[diff]!.action) }}</div>
                <div class="suggestion-reasoning">{{ aiSuggestions[diff]!.reasoning.substring(0, 200) }}</div>
                <div class="suggestion-source">via {{ aiSuggestions[diff]!.source }}</div>
              </template>
              <div v-else class="suggestion-empty">No suggestion</div>
            </div>
          </div>
        </div>

        <div v-else class="debug-empty">
          <p>Play a move to see AI analysis.</p>
          <p class="debug-hint">Press <kbd>`</kbd> to toggle this panel.</p>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.debug-toggle-btn {
  position: fixed;
  top: 50%;
  right: 0;
  transform: translateY(-50%);
  z-index: 200;
  width: 32px;
  height: 48px;
  background: var(--parchment-dark);
  border: 1px solid var(--parchment-deep);
  border-right: none;
  border-radius: var(--radius-sm) 0 0 var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.2s ease;
}

.debug-toggle-btn:hover {
  background: var(--parchment-deep);
}

.debug-icon {
  font-size: 1.1rem;
  color: var(--ink-faint);
}

.debug-panel {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 360px;
  max-width: 90vw;
  z-index: 201;
  background: rgba(244, 236, 224, 0.95);
  backdrop-filter: blur(8px);
  border-left: 2px solid var(--parchment-deep);
  box-shadow: -4px 0 24px rgba(44, 24, 16, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.debug-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--gap-md) var(--gap-lg);
  border-bottom: 1px solid var(--parchment-deep);
  background: var(--parchment-dark);
}

.debug-title {
  font-family: var(--font-display);
  font-size: 1.1rem;
  color: var(--forest-dark);
  margin: 0;
}

.debug-close {
  font-size: 1.5rem;
  color: var(--ink-faint);
  cursor: pointer;
  background: none;
  border: none;
  line-height: 1;
  padding: 0 4px;
  transition: color 0.2s ease;
}

.debug-close:hover {
  color: var(--ink);
}

.debug-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--gap-lg);
}

.debug-loading {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  color: var(--ink-faint);
  font-style: italic;
}

.debug-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid var(--parchment-deep);
  border-top-color: var(--forest-light);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.debug-error {
  color: var(--red-destination);
  font-size: 0.9rem;
  padding: var(--gap-sm);
  background: var(--red-destination-bg);
  border-radius: var(--radius-sm);
}

.quality-badge {
  display: inline-block;
  padding: 6px 16px;
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  margin-bottom: var(--gap-md);
}

.quality-brilliant {
  background: linear-gradient(135deg, #ffd700, #ffb800);
  color: #5a3e00;
  box-shadow: 0 0 16px rgba(255, 215, 0, 0.5), 0 0 32px rgba(255, 215, 0, 0.2);
  animation: pulse-glow 2s ease-in-out infinite;
}

@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 16px rgba(255, 215, 0, 0.5), 0 0 32px rgba(255, 215, 0, 0.2); }
  50% { box-shadow: 0 0 24px rgba(255, 215, 0, 0.7), 0 0 48px rgba(255, 215, 0, 0.3); }
}

.quality-good {
  background: var(--green-production-bg);
  color: var(--green-production);
  border: 1.5px solid var(--green-production);
}

.quality-inaccuracy {
  background: #fef8e0;
  color: #8a6d00;
  border: 1.5px solid #d4a800;
}

.quality-mistake {
  background: #fef0e0;
  color: #9a4a00;
  border: 1.5px solid #d47b00;
}

.quality-blunder {
  background: var(--red-destination-bg);
  color: var(--red-destination);
  border: 1.5px solid var(--red-destination);
}

.eval-explanation {
  font-size: 0.92rem;
  color: var(--ink-light);
  line-height: 1.6;
  margin-bottom: var(--gap-lg);
}

.eval-alternatives {
  border-top: 1px solid var(--parchment-deep);
  padding-top: var(--gap-md);
}

.alt-heading {
  font-family: var(--font-display);
  font-size: 0.85rem;
  color: var(--ink-faint);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--gap-sm);
}

.alt-item {
  padding: var(--gap-sm) var(--gap-md);
  background: white;
  border: var(--border-card);
  border-radius: var(--radius-sm);
  margin-bottom: var(--gap-sm);
}

.alt-action {
  font-weight: 600;
  font-size: 0.88rem;
  color: var(--ink);
  margin-bottom: 2px;
}

.alt-desc {
  font-size: 0.82rem;
  color: var(--ink-faint);
  line-height: 1.4;
}

.alt-delta {
  font-family: var(--font-display);
  font-size: 0.8rem;
  color: var(--red-destination);
  margin-top: 4px;
}

.alt-delta.positive {
  color: var(--green-production);
}

.debug-empty {
  text-align: center;
  color: var(--ink-faint);
  font-style: italic;
  padding: var(--gap-xl) 0;
}

.debug-empty p {
  margin-bottom: var(--gap-sm);
}

.debug-hint {
  font-size: 0.82rem;
}

.debug-hint kbd {
  display: inline-block;
  padding: 2px 6px;
  background: var(--parchment-dark);
  border: 1px solid var(--parchment-deep);
  border-radius: 3px;
  font-family: monospace;
  font-size: 0.85rem;
  font-style: normal;
}

/* AI Suggestions */
.ai-suggestions {
  border-top: 1px solid var(--parchment-deep);
  padding-top: var(--gap-md);
  margin-top: var(--gap-md);
}

.suggestions-heading {
  font-family: var(--font-display);
  font-size: 0.85rem;
  color: var(--ink-faint);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--gap-sm);
}

.suggestion-cards {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.suggestion-card {
  padding: var(--gap-sm) var(--gap-md);
  background: white;
  border: var(--border-card);
  border-radius: var(--radius-sm);
}

.suggestion-diff {
  font-family: var(--font-display);
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: capitalize;
  letter-spacing: 0.03em;
  margin-bottom: 4px;
}

.diff-apprentice { color: var(--forest-light); }
.diff-journeyman { color: var(--gold); }
.diff-master { color: var(--purple-prosperity); }

.suggestion-action {
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--ink);
  margin-bottom: 2px;
}

.suggestion-reasoning {
  font-size: 0.78rem;
  color: var(--ink-faint);
  line-height: 1.4;
}

.suggestion-source {
  font-size: 0.65rem;
  color: var(--ink-faint);
  margin-top: 4px;
  font-style: italic;
}

.suggestion-empty {
  font-size: 0.8rem;
  color: var(--ink-faint);
  font-style: italic;
}

/* Slide transition */
.slide-right-enter-active,
.slide-right-leave-active {
  transition: transform 0.3s ease;
}

.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(100%);
}
</style>
