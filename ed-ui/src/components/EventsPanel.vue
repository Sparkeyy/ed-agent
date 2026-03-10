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
  'event-info': [eventData: { name: string; description?: string; required_cards?: string[]; points: number }]
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

function eventDescription(eventData: any): string {
  if (eventData && typeof eventData === 'object' && eventData.description) {
    return eventData.description
  }
  return ''
}

function emitEventInfo(eventData: any, eventId: string) {
  emit('event-info', {
    name: eventName(eventData, String(eventId)),
    description: eventDescription(eventData),
    required_cards: eventData?.required_cards,
    points: eventPoints(eventData),
  })
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
          <button class="event-info-btn" @click.stop="emitEventInfo(data, String(eventId))" title="Event info">i</button>
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
          <button class="event-info-btn" @click.stop="emitEventInfo(data, String(eventId))" title="Event info">i</button>
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
  font-size: 0.78rem;
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

.event-info-btn {
  position: absolute;
  top: 3px;
  right: 3px;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1px solid var(--ink-faint);
  background: rgba(255, 255, 255, 0.8);
  color: var(--ink-faint);
  font-size: 0.5rem;
  font-weight: 700;
  font-style: italic;
  font-family: serif;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.event-card:hover .event-info-btn {
  opacity: 1;
}

.event-info-btn:hover {
  background: var(--gold);
  color: white;
  border-color: var(--gold);
}

.event-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 12px;
  background: var(--parchment-dark);
  border: 1.5px solid var(--parchment-deep);
  border-radius: var(--radius-md);
  min-width: 140px;
  max-width: 200px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.event-card:not(.basic) {
  border-left: 3px solid var(--purple-prosperity);
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
  opacity: 0.6;
}

.event-card-name {
  font-family: var(--font-card);
  font-weight: 600;
  font-size: 0.8rem;
  color: var(--ink);
  line-height: 1.2;
}

.event-card-req {
  font-size: 0.7rem;
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
