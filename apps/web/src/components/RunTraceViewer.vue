<template>
  <section v-if="run" class="run-trace" aria-label="Run trace viewer">
    <header class="run-trace__header">
      <div>
        <span class="run-trace__eyebrow">Trace</span>
        <strong>{{ run.runId }}</strong>
      </div>
      <span class="run-trace__status" :data-status="run.status">{{ run.status }}</span>
    </header>

    <div class="run-trace__events">
      <details
        v-for="event in events"
        :key="event.id"
        class="run-trace__event"
      >
        <summary>
          <span>{{ event.eventType }}</span>
          <time>{{ formatEventTime(event.createdAt) }}</time>
        </summary>
        <pre>{{ formatPayload(event.payload) }}</pre>
      </details>
    </div>
  </section>
</template>

<script setup>
import { computed } from "vue";

import { formatEventTime } from "../composables/useChatClient";

const props = defineProps({
  run: {
    type: Object,
    default: null,
  },
});

const events = computed(() => props.run?.rawEvents || props.run?.events || []);

function formatPayload(payload) {
  try {
    return JSON.stringify(payload || {}, null, 2);
  } catch {
    return String(payload || "");
  }
}
</script>
