<script setup lang="ts">
import { ref } from 'vue'

const props = withDefaults(defineProps<{
  events: {
    basic_events: Record<string, any>
    special_events: Record<string, any>
  }
  claimableEventIds?: string[]
}>(), {
  claimableEventIds: () => [],
})

const emit = defineEmits<{
  'claim-event': [eventId: string]
}>()

const collapsed = ref(false)

function isClaimable(eventId: string): boolean {
  return props.claimableEventIds.includes(eventId)
}

function isClaimed(eventData: any): boolean {
  return eventData && typeof eventData === 'object' && eventData.claimed_by
}

function claimerName(eventData: any): string {
  if (eventData && typeof eventData === 'object' && eventData.claimed_by) {
    return eventData.claimed_by
  }
  return ''
}
</script>

<template>
  <div class="events-panel" :class="{ collapsed }">
    <button class="panel-toggle" @click="collapsed = !collapsed">
      <span class="toggle-icon">{{ collapsed ? '\u25B6' : '\u25BC' }}</span>
      <span class="toggle-label">Events</span>
    </button>
    <div v-if="!collapsed" class="events-content">
      <div class="event-section">
        <h4 class="event-section-title">Basic Events</h4>
        <div
          v-for="(data, eventId) in events.basic_events"
          :key="'basic-' + eventId"
          class="event-item"
          :class="{ claimable: isClaimable(String(eventId)), claimed: isClaimed(data) }"
          @click="isClaimable(String(eventId)) && emit('claim-event', String(eventId))"
        >
          <span class="event-name">{{ eventId }}</span>
          <span v-if="isClaimed(data)" class="claimed-badge">\u2713 {{ claimerName(data) }}</span>
        </div>
      </div>
      <div class="event-section">
        <h4 class="event-section-title">Special Events</h4>
        <div
          v-for="(data, eventId) in events.special_events"
          :key="'special-' + eventId"
          class="event-item"
          :class="{ claimable: isClaimable(String(eventId)), claimed: isClaimed(data) }"
          @click="isClaimable(String(eventId)) && emit('claim-event', String(eventId))"
        >
          <span class="event-name">{{ eventId }}</span>
          <span v-if="isClaimed(data)" class="claimed-badge">\u2713 {{ claimerName(data) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.events-panel {
  background: var(--parchment-dark);
  border: var(--border-card);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.panel-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  padding: var(--gap-sm) var(--gap-md);
  font-family: var(--font-display);
  font-size: 0.9rem;
  color: var(--ink);
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
}

.panel-toggle:hover {
  background: var(--parchment-deep);
}

.toggle-icon {
  font-size: 0.65rem;
  color: var(--ink-faint);
}

.events-content {
  padding: 0 var(--gap-md) var(--gap-md);
}

.event-section {
  margin-bottom: var(--gap-sm);
}

.event-section-title {
  font-family: var(--font-display);
  font-size: 0.75rem;
  color: var(--ink-faint);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: var(--gap-xs);
}

.event-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px var(--gap-sm);
  border-radius: var(--radius-sm);
  font-size: 0.78rem;
  margin-bottom: 2px;
  transition: background 0.2s ease, box-shadow 0.2s ease;
}

.event-item.claimable {
  animation: pulse-glow 2s ease-in-out infinite;
  cursor: pointer;
  background: rgba(201, 169, 110, 0.1);
  border: 1px solid var(--gold);
  border-radius: var(--radius-sm);
}

.event-item.claimable:hover {
  background: rgba(201, 169, 110, 0.2);
}

.event-item.claimed {
  opacity: 0.6;
}

.event-name {
  font-family: var(--font-card);
  color: var(--ink);
}

.claimed-badge {
  font-size: 0.68rem;
  color: var(--forest-light);
  font-weight: 600;
}
</style>
