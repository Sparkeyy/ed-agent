<script setup lang="ts">
import { ref, nextTick, onMounted, onUnmounted } from 'vue'
import { useGameStore } from '../stores/game'
import { chatAi } from '../api/client'

const store = useGameStore()
const visible = ref(false)
const activeTab = ref<'rules' | 'ask'>('rules')

// Chat state
const messages = ref<Array<{ role: 'user' | 'ai'; text: string }>>([])
const chatInput = ref('')
const chatLoading = ref(false)
const chatScroll = ref<HTMLElement | null>(null)

function toggle() {
  visible.value = !visible.value
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === '?' && !e.ctrlKey && !e.metaKey && !e.altKey) {
    const tag = (e.target as HTMLElement)?.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
    e.preventDefault()
    toggle()
  }
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onUnmounted(() => window.removeEventListener('keydown', handleKeydown))

async function sendChat() {
  const q = chatInput.value.trim()
  if (!q || chatLoading.value) return
  chatInput.value = ''
  messages.value.push({ role: 'user', text: q })
  chatLoading.value = true
  await nextTick()
  scrollChat()

  try {
    const ctx = store.state ? { turn: store.state.turn_number, season: store.myPlayer?.season } : undefined
    const resp = await chatAi(q, ctx)
    messages.value.push({ role: 'ai', text: resp.answer })
  } catch {
    messages.value.push({ role: 'ai', text: 'Failed to reach AI assistant. Check the Rules tab for reference.' })
  } finally {
    chatLoading.value = false
    await nextTick()
    scrollChat()
  }
}

function scrollChat() {
  if (chatScroll.value) {
    chatScroll.value.scrollTop = chatScroll.value.scrollHeight
  }
}
</script>

<template>
  <div class="help-toggle-btn" @click="toggle" title="Help (?)">
    <span class="help-icon">?</span>
  </div>

  <Transition name="slide-left">
    <div v-if="visible" class="help-panel">
      <div class="help-header">
        <h3 class="help-title">Help</h3>
        <div class="help-tabs">
          <button class="tab-btn" :class="{ active: activeTab === 'rules' }" @click="activeTab = 'rules'">Rules</button>
          <button class="tab-btn" :class="{ active: activeTab === 'ask' }" @click="activeTab = 'ask'">Ask</button>
        </div>
        <button class="help-close" @click="toggle">&times;</button>
      </div>

      <!-- Rules Tab -->
      <div v-if="activeTab === 'rules'" class="help-body rules-body">
        <details open>
          <summary>Overview</summary>
          <p>Everdell is a worker placement and tableau-building game for 1-4 players. Build a city of up to 15 cards across 4 seasons, earning victory points through cards, events, and special abilities.</p>
        </details>

        <details>
          <summary>Seasons & Workers</summary>
          <p><strong>Winter:</strong> 2 workers. <strong>Spring:</strong> +1 worker (3 total). <strong>Summer:</strong> +1 worker (4 total). <strong>Autumn:</strong> +2 workers (6 total).</p>
          <p>Workers are placed on locations to gain resources. They return when you <em>Prepare for Season</em>.</p>
        </details>

        <details>
          <summary>On Your Turn</summary>
          <p>Choose ONE action:</p>
          <ul>
            <li><strong>Place a Worker</strong> on a location</li>
            <li><strong>Play a Card</strong> from hand or Meadow (pay its cost)</li>
            <li><strong>Prepare for Season</strong> (retrieve workers, gain season bonuses, activate production)</li>
          </ul>
        </details>

        <details>
          <summary>Card Types (5 colors)</summary>
          <ul class="type-list">
            <li><span class="type-dot" style="background:#a08060"></span> <strong>Tan / Traveler:</strong> One-time effect when played</li>
            <li><span class="type-dot" style="background:#4a7c59"></span> <strong>Green / Production:</strong> Activates each season during Prepare</li>
            <li><span class="type-dot" style="background:#a83832"></span> <strong>Red / Destination:</strong> Place a worker to activate</li>
            <li><span class="type-dot" style="background:#3a6b8c"></span> <strong>Blue / Governance:</strong> Ongoing passive effect</li>
            <li><span class="type-dot" style="background:#6b4c7a"></span> <strong>Purple / Prosperity:</strong> Bonus VP at game end</li>
          </ul>
        </details>

        <details>
          <summary>Card Categories</summary>
          <p><strong>Constructions</strong> cost resources (twigs, resin, pebble). <strong>Critters</strong> cost berries. Some critters can be played for free if their paired construction is in your city.</p>
          <p><strong>Unique</strong> cards: only 1 per city. <strong>Common</strong> cards: multiple allowed.</p>
        </details>

        <details>
          <summary>Locations</summary>
          <ul>
            <li><strong>Basic:</strong> Always available. Some shared (unlimited workers), some exclusive (1 worker).</li>
            <li><strong>Forest:</strong> 3-4 per game. All exclusive.</li>
            <li><strong>Haven:</strong> Discard 2 cards for 1 resource of any type.</li>
            <li><strong>Journey:</strong> Autumn only. Discard cards to score VP.</li>
          </ul>
        </details>

        <details>
          <summary>Events</summary>
          <p><strong>Basic Events (4):</strong> Available to all. Claim when you meet the requirement.</p>
          <p><strong>Special Events (4):</strong> Require specific card combinations in your city.</p>
        </details>

        <details>
          <summary>Prepare for Season</summary>
          <p>When you have no more useful actions: retrieve all workers, advance to next season, activate all green Production cards, gain new workers.</p>
        </details>

        <details>
          <summary>Game End & Scoring</summary>
          <p>After all players complete Autumn and pass, the game ends. Score:</p>
          <ul>
            <li>Base VP on each card in your city</li>
            <li>Purple Prosperity card bonuses</li>
            <li>Event VP (basic + special)</li>
            <li>Journey VP</li>
            <li>VP tokens from abilities</li>
          </ul>
        </details>
      </div>

      <!-- Ask Tab -->
      <div v-if="activeTab === 'ask'" class="help-body ask-body">
        <div ref="chatScroll" class="chat-messages">
          <div v-if="messages.length === 0" class="chat-empty">
            Ask anything about Everdell rules, card abilities, or strategy.
          </div>
          <div
            v-for="(msg, i) in messages"
            :key="i"
            class="chat-msg"
            :class="msg.role"
          >
            <div class="msg-text">{{ msg.text }}</div>
          </div>
          <div v-if="chatLoading" class="chat-msg ai">
            <div class="msg-text loading-dots">Thinking...</div>
          </div>
        </div>
        <div class="chat-input-row">
          <input
            v-model="chatInput"
            class="chat-input"
            placeholder="Ask about rules..."
            @keydown.enter="sendChat"
          >
          <button class="chat-send" @click="sendChat" :disabled="chatLoading || !chatInput.trim()">Send</button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.help-toggle-btn {
  position: fixed;
  top: 50%;
  left: 0;
  transform: translateY(-50%);
  z-index: 200;
  width: 32px;
  height: 48px;
  background: var(--parchment-dark);
  border: 1px solid var(--parchment-deep);
  border-left: none;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.2s ease;
}

.help-toggle-btn:hover {
  background: var(--parchment-deep);
}

.help-icon {
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--ink-faint);
}

.help-panel {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 380px;
  max-width: 90vw;
  z-index: 201;
  background: rgba(244, 236, 224, 0.95);
  backdrop-filter: blur(8px);
  border-right: 2px solid var(--parchment-deep);
  box-shadow: 4px 0 24px rgba(44, 24, 16, 0.15);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.help-header {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  padding: var(--gap-md) var(--gap-lg);
  border-bottom: 1px solid var(--parchment-deep);
  background: var(--parchment-dark);
}

.help-title {
  font-family: var(--font-display);
  font-size: 1.1rem;
  color: var(--forest-dark);
  margin: 0;
  margin-right: auto;
}

.help-tabs {
  display: flex;
  gap: 2px;
}

.tab-btn {
  padding: 4px 12px;
  font-family: var(--font-display);
  font-size: 0.78rem;
  border: 1px solid var(--parchment-deep);
  background: none;
  color: var(--ink-faint);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all 0.2s ease;
}

.tab-btn.active {
  background: var(--forest-light);
  color: white;
  border-color: var(--forest-light);
}

.help-close {
  font-size: 1.5rem;
  color: var(--ink-faint);
  cursor: pointer;
  background: none;
  border: none;
  line-height: 1;
  padding: 0 4px;
}

.help-close:hover {
  color: var(--ink);
}

.help-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--gap-md) var(--gap-lg);
}

/* Rules tab */
.rules-body details {
  margin-bottom: var(--gap-sm);
  border: 1px solid var(--parchment-deep);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.rules-body summary {
  padding: 8px 12px;
  font-family: var(--font-display);
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--forest-dark);
  cursor: pointer;
  background: var(--parchment-dark);
  user-select: none;
}

.rules-body summary:hover {
  background: var(--parchment-deep);
}

.rules-body details > p,
.rules-body details > ul {
  padding: 8px 12px;
  font-size: 0.82rem;
  color: var(--ink-light);
  line-height: 1.5;
  margin: 0;
}

.rules-body ul {
  padding-left: 20px;
}

.rules-body li {
  margin-bottom: 4px;
}

.type-list {
  list-style: none;
  padding-left: 0 !important;
}

.type-list li {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.type-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  position: relative;
  top: 1px;
}

/* Ask tab */
.ask-body {
  display: flex;
  flex-direction: column;
  padding: 0;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--gap-md) var(--gap-lg);
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.chat-empty {
  text-align: center;
  color: var(--ink-faint);
  font-style: italic;
  padding: var(--gap-xl) 0;
  font-size: 0.85rem;
}

.chat-msg {
  max-width: 85%;
  padding: 8px 12px;
  border-radius: var(--radius-md);
  font-size: 0.85rem;
  line-height: 1.5;
}

.chat-msg.user {
  align-self: flex-end;
  background: var(--forest-light);
  color: white;
  border-bottom-right-radius: 2px;
}

.chat-msg.ai {
  align-self: flex-start;
  background: white;
  color: var(--ink);
  border: 1px solid var(--parchment-deep);
  border-bottom-left-radius: 2px;
}

.loading-dots {
  font-style: italic;
  color: var(--ink-faint);
}

.chat-input-row {
  display: flex;
  gap: var(--gap-sm);
  padding: var(--gap-sm) var(--gap-lg);
  border-top: 1px solid var(--parchment-deep);
  background: var(--parchment-dark);
}

.chat-input {
  flex: 1;
  padding: 8px 12px;
  border: 1.5px solid var(--parchment-deep);
  border-radius: var(--radius-md);
  font-family: var(--font-body);
  font-size: 0.85rem;
  background: white;
  color: var(--ink);
}

.chat-input:focus {
  outline: none;
  border-color: var(--forest-light);
}

.chat-send {
  padding: 8px 16px;
  background: var(--forest-light);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.chat-send:hover:not(:disabled) {
  background: var(--forest-dark);
}

.chat-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Slide transition */
.slide-left-enter-active,
.slide-left-leave-active {
  transition: transform 0.3s ease;
}

.slide-left-enter-from,
.slide-left-leave-to {
  transform: translateX(-100%);
}
</style>
