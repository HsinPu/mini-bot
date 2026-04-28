<template>
  <section class="run-timeline" :data-tone="summary.tone" aria-live="polite">
    <div class="run-timeline__header">
      <div>
        <span class="run-timeline__eyebrow">Run {{ summary.shortId }}</span>
        <strong>{{ summary.title }}</strong>
      </div>
      <span class="run-timeline__status">{{ summary.statusLabel }}</span>
    </div>

    <ol class="run-timeline__list">
      <li
        v-for="event in events"
        :key="event.id"
        class="run-timeline__item"
        :data-tone="event.tone"
      >
        <span class="run-timeline__dot" aria-hidden="true"></span>
        <div class="run-timeline__text">
          <strong>{{ event.label }}</strong>
          <span v-if="event.detail">{{ event.detail }}</span>
        </div>
        <time>{{ formatEventTime(event.createdAt) }}</time>
      </li>
    </ol>
  </section>
</template>

<script setup>
import { formatEventTime } from "../composables/useChatClient";

defineProps({
  summary: {
    type: Object,
    required: true,
  },
  events: {
    type: Array,
    required: true,
  },
});
</script>
