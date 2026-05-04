<template>
  <section class="curator-card" aria-live="polite">
    <div class="curator-card__header">
      <div>
        <span>{{ copy.curator.eyebrow }}</span>
        <strong>{{ copy.curator.title }}</strong>
      </div>
      <button class="ghost-button" type="button" :disabled="state.loading" @click="$emit('refresh-curator')">
        {{ state.loading ? copy.curator.loading : copy.curator.refresh }}
      </button>
    </div>

    <p v-if="state.error" class="curator-card__error">{{ state.error }}</p>
    <dl class="curator-card__grid">
      <div>
        <dt>{{ copy.curator.state }}</dt>
        <dd>{{ status?.state || copy.curator.unknown }}</dd>
      </div>
      <div>
        <dt>{{ copy.curator.paused }}</dt>
        <dd>{{ status?.paused ? copy.curator.yes : copy.curator.no }}</dd>
      </div>
      <div>
        <dt>{{ copy.curator.currentJob }}</dt>
        <dd :title="currentCuratorJobLabel">{{ currentCuratorJobLabel }}</dd>
      </div>
      <div>
        <dt>{{ copy.curator.runCount }}</dt>
        <dd>{{ status?.run_count || 0 }}</dd>
      </div>
      <div>
        <dt>{{ copy.curator.lastRun }}</dt>
        <dd>{{ status?.last_run_at || copy.curator.never }}</dd>
      </div>
      <div>
        <dt>{{ copy.curator.lastJobs }}</dt>
        <dd :title="lastCuratorJobsLabel">{{ lastCuratorJobsLabel }}</dd>
      </div>
      <div>
        <dt>{{ copy.curator.lastChanged }}</dt>
        <dd :title="lastCuratorChangedLabel">{{ lastCuratorChangedLabel }}</dd>
      </div>
    </dl>
    <p class="curator-card__summary">
      {{ status?.last_run_summary || copy.curator.noSummary }}
    </p>
    <p v-if="status?.last_error" class="curator-card__error">{{ copy.curator.lastError }}: {{ status.last_error }}</p>
    <label class="curator-card__scope">
      <span>{{ copy.curator.scope }}</span>
      <select v-model="selectedCuratorScope" :disabled="Boolean(state.action || state.loading)">
        <option v-for="option in curatorScopeOptions" :key="option.value" :value="option.value">
          {{ option.label }}
        </option>
      </select>
    </label>
    <div class="curator-card__actions">
      <button
        class="secondary-button"
        type="button"
        :disabled="actionsDisabled"
        @click="$emit('run-curator-action', { action: 'run', scope: selectedCuratorScope === 'all' ? '' : selectedCuratorScope })"
      >
        {{ state.action === 'run' ? copy.curator.running : copy.curator.run }}
      </button>
      <button class="secondary-button" type="button" :disabled="actionsDisabled || status?.paused" @click="$emit('run-curator-action', 'pause')">
        {{ state.action === 'pause' ? copy.curator.pausing : copy.curator.pause }}
      </button>
      <button class="secondary-button" type="button" :disabled="actionsDisabled || !status?.paused" @click="$emit('run-curator-action', 'resume')">
        {{ state.action === 'resume' ? copy.curator.resuming : copy.curator.resume }}
      </button>
    </div>
    <section class="curator-card__history" aria-live="polite">
      <div class="curator-card__history-head">
        <strong>{{ copy.curator.historyTitle }}</strong>
        <small v-if="state.historyLoading">{{ copy.curator.historyLoading }}</small>
      </div>
      <div v-if="curatorHistoryEntries.length" class="curator-card__history-list">
        <article v-for="entry in curatorHistoryEntries" :key="entry.key" class="curator-card__history-entry">
          <div class="curator-card__history-meta">
            <strong>{{ entry.runAt }}</strong>
            <span>{{ entry.statusLabel }}</span>
          </div>
          <p>{{ entry.summary }}</p>
          <small>{{ copy.curator.lastJobs }}: {{ entry.jobs }}</small>
          <small v-if="entry.changed">{{ copy.curator.lastChanged }}: {{ entry.changed }}</small>
          <small v-if="entry.error">{{ copy.curator.lastError }}: {{ entry.error }}</small>
        </article>
      </div>
      <p v-else class="curator-card__history-empty">{{ state.historyError || copy.curator.historyEmpty }}</p>
    </section>
  </section>
</template>

<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  copy: {
    type: Object,
    required: true,
  },
  state: {
    type: Object,
    required: true,
  },
  status: {
    type: Object,
    default: null,
  },
});

defineEmits(["refresh-curator", "run-curator-action"]);

const selectedCuratorScope = ref("all");

const actionsDisabled = computed(() => {
  return Boolean(props.state.action || props.state.loading || props.state.error || !props.status);
});

const curatorScopeOptions = computed(() => {
  const labels = props.copy.curator.scopes || {};
  return [
    { value: "all", label: labels.all || "all" },
    { value: "maintenance", label: labels.maintenance || "maintenance" },
    { value: "skills", label: labels.skills || "skills" },
    { value: "memory", label: labels.memory || "memory" },
    { value: "recent_summary", label: labels.recent_summary || "recent_summary" },
    { value: "user_profile", label: labels.user_profile || "user_profile" },
    { value: "active_task", label: labels.active_task || "active_task" },
  ];
});

const currentCuratorJobLabel = computed(() => {
  return String(props.status?.current_job_label || props.status?.current_job || "").trim() || props.copy.curator.none;
});

const lastCuratorJobsLabel = computed(() => {
  const jobs = Array.isArray(props.status?.last_run_jobs) ? props.status.last_run_jobs : [];
  return jobs.length ? jobs.join(", ") : props.copy.curator.none;
});

const lastCuratorChangedLabel = computed(() => {
  const changed = Array.isArray(props.status?.last_run_changed) ? props.status.last_run_changed : [];
  return changed.length ? changed.join(", ") : props.copy.curator.none;
});

const curatorHistoryEntries = computed(() => {
  const entries = Array.isArray(props.state.history) ? props.state.history : [];
  return entries.map((entry, index) => ({
    key: `${entry.run_id || "history"}:${entry.run_at || index}:${index}`,
    runAt: formatCuratorHistoryTime(entry.run_at),
    statusLabel: props.copy.run.statusLabels[String(entry.status || "").trim()] || String(entry.status || props.copy.curator.unknown),
    summary: String(entry.summary || "").trim() || props.copy.curator.noSummary,
    jobs: Array.isArray(entry.jobs) && entry.jobs.length ? entry.jobs.join(", ") : props.copy.curator.none,
    changed: Array.isArray(entry.changed) && entry.changed.length ? entry.changed.join(", ") : "",
    error: String(entry.error || "").trim(),
  }));
});

function formatCuratorHistoryTime(value) {
  const normalized = String(value || "").trim();
  const date = new Date(normalized);
  if (!normalized || Number.isNaN(date.getTime())) {
    return normalized || props.copy.curator.unknown;
  }
  return date.toLocaleString();
}
</script>
