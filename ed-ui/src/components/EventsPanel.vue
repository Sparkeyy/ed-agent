<script setup lang="ts">
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

function eventName(eventData: any, fallback: string): string {
  if (eventData && typeof eventData === 'object' && eventData.name) {
    return eventData.name
  }
  return fallback
}

function eventRequires(eventData: any): string {
  if (eventData && typeof eventData === 'object' && eventData.required_cards) {
    return eventData.required_cards.join(' + ')
  }
  return ''
}

function eventPoints(eventData: any): number {
  if (eventData && typeof eventData === 'object' && eventData.points) {
    return eventData.points
  }
  return 0
}
</script>

<template>
  <div class="events-row">
    <!-- Special Events -->
    <div class="events-group">
      <h4 class="events-group-title">Special Events</h4>
      <div class="events-cards">
        <div
          v-for="(data, eventId) in events.special_events"
          :key="'special-' + eventId"
          class="event-card"
          :class="{ claimable: isClaimable(String(eventId)), claimed: isClaimed(data) }"
          @click="isClaimable(String(eventId)) && emit('claim-event', String(eventId))"
        >
          <div class="event-card-name">{{ eventName(data, String(eventId)) }}</div>
          <div class="event-card-req">{{ eventRequires(data) }}</div>
          <div class="event-card-footer">
            <span class="event-card-pts">{{ eventPoints(data) }} VP</span>
            <span v-if="isClaimed(data)" class="event-card-claimed">{{ claimerName(data) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Basic Events -->
    <div class="events-group">
      <h4 class="events-group-title">Basic Events</h4>
      <div class="events-cards">
        <div
          v-for="(data, eventId) in events.basic_events"
          :key="'basic-' + eventId"
          class="event-card basic"
          :class="{ claimable: isClaimable(String(eventId)), claimed: isClaimed(data) }"
          @click="isClaimable(String(eventId)) && emit('claim-event', String(eventId))"
        >
          <div class="event-card-name">{{ eventName(data, String(eventId)) }}</div>
          <div class="event-card-footer">
            <span class="event-card-pts">{{ eventPoints(data) }} VP</span>
            <span v-if="isClaimed(data)" class="event-card-claimed">{{ claimerName(data) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.events-row {
  display: flex;
  gap: var(--gap-md);
  width: 100%;
  max-width: 900px;
  flex-wrap: wrap;
  justify-content: center;
}

.events-group {
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
}

.events-group-title {
  font-family: var(--font-display);
  font-size: 0.7rem;
  color: var(--ink-faint);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  text-align: center;
}

.events-cards {
  display: flex;
  gap: var(--gap-sm);
  flex-wrap: wrap;
  justify-content: center;
}

.event-card {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 10px;
  background: var(--parchment-dark);
  border: 1.5px solid var(--parchment-deep);
  border-radius: var(--radius-md);
  min-width: 120px;
  max-width: 160px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.event-card.basic {
  border-left: 3px solid var(--gold, #c9a96e);
}

.event-card.claimable {
  animation: pulse-glow 2s ease-in-out infinite;
  cursor: pointer;
  border-color: var(--gold);
  background: rgba(201, 169, 110, 0.08);
}

.event-card.claimable:hover {
  box-shadow: var(--shadow-glow);
}

.event-card.claimed {
  opacity: 0.45;
}

.event-card-name {
  font-family: var(--font-card);
  font-weight: 600;
  font-size: 0.72rem;
  color: var(--ink);
  line-height: 1.2;
}

.event-card-req {
  font-size: 0.6rem;
  color: var(--ink-faint);
  line-height: 1.2;
}

.event-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 2px;
}

.event-card-pts {
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--gold, #c9a96e);
}

.event-card-claimed {
  font-size: 0.6rem;
  font-weight: 600;
  color: var(--forest-light);
  background: var(--green-production-bg, rgba(74, 124, 89, 0.1));
  padding: 1px 4px;
  border-radius: var(--radius-sm);
}
</style>
