<template>
  <div class="message-list">
    <article
      v-for="message in messages"
      :key="message.id"
      class="message"
      :class="`message--${message.role}`"
    >
      <div class="message__avatar">{{ message.role === "user" ? copy.message.userAvatar : copy.message.assistantAvatar }}</div>
      <div class="message__content">
        <div class="message__meta">
          {{ message.meta || (message.role === "user" ? displayName : "OpenSprite") }}
        </div>
        <div v-if="message.text" class="message__bubble">{{ message.text }}</div>
        <div v-if="message.content.length" class="message__parts">
          <template v-for="part in message.content" :key="part.id">
            <div v-if="part.type === 'text'" class="message__bubble">{{ part.text || part.detail }}</div>
            <div v-else class="message__artifact" :data-type="part.type" :data-status="part.status || undefined">
              <div class="message__artifact-header">
                <span class="message__artifact-type">{{ artifactTypeLabel(part.type) }}</span>
                <small v-if="part.status" class="message__artifact-status">{{ artifactStatusLabel(part.status) }}</small>
              </div>
              <strong>{{ part.title || artifactTypeLabel(part.type) }}</strong>
              <p v-if="part.detail">{{ part.detail }}</p>
            </div>
          </template>
        </div>
      </div>
    </article>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  copy: {
    type: Object,
    required: true,
  },
  entries: {
    type: Array,
    default: () => [],
  },
  messages: {
    type: Array,
    required: true,
  },
  displayName: {
    type: String,
    required: true,
  },
});

const INTERNAL_BLOCK_RE = /<\s*(think|thinking|system-reminder)\b[^>]*>[\s\S]*?<\s*\/\s*\1\s*>/gi;
const INTERNAL_OPEN_BLOCK_RE = /<\s*(think|thinking|system-reminder)\b[^>]*>[\s\S]*$/i;

function sanitizeVisibleText(value) {
  return String(value || "")
    .replace(INTERNAL_BLOCK_RE, "")
    .replace(INTERNAL_OPEN_BLOCK_RE, "")
    .trim();
}

function normalizeTextPart(part, index) {
  const text = sanitizeVisibleText(part?.text || part?.detail || "");
  if (!text) {
    return null;
  }
  return {
    id: part?.id || `text-${index}`,
    type: "text",
    text,
  };
}

function normalizeEntry(entry, index) {
  const role = entry.role === "user" ? "user" : "assistant";
  const content = Array.isArray(entry.content)
    ? entry.content.map(normalizeTextPart).filter(Boolean)
    : [];
  const text = sanitizeVisibleText(entry.text || "");

  if (!text && content.length === 0) {
    return null;
  }

  return {
    id: entry.id || `entry-${index}`,
    role,
    text,
    meta: entry.meta || (role === "user" ? props.displayName : "OpenSprite"),
    content,
  };
}

function normalizeMessage(message) {
  return {
    ...message,
    text: sanitizeVisibleText(message.text),
    content: [],
  };
}

const messages = computed(() => {
  if (props.entries.length) {
    return props.entries.map(normalizeEntry).filter(Boolean);
  }

  return props.messages.map(normalizeMessage).filter((message) => message.text.trim());
});

function artifactTypeLabel(type) {
  const labels = props.copy.message.artifactTypes || {};
  return labels[type] || type;
}

function artifactStatusLabel(status) {
  const labels = props.copy.run?.statusLabels || {};
  return labels[status] || status;
}
</script>
