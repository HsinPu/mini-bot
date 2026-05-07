<template>
  <aside class="sidebar" id="sidebar" :aria-label="copy.sidebar.ariaLabel">
    <div class="sidebar__top">
      <div class="brand-row">
        <div class="brand-mark" aria-hidden="true">OS</div>
        <div class="brand-row__copy">
          <strong>OpenSprite</strong>
          <span>{{ copy.sidebar.brandSubtitle }}</span>
        </div>
        <button
          class="sidebar-collapse-button"
          type="button"
          :aria-label="collapsed ? copy.sidebar.expand : copy.sidebar.collapse"
          :title="collapsed ? copy.sidebar.expand : copy.sidebar.collapse"
          :aria-pressed="String(collapsed)"
          @click="$emit('toggle-sidebar-collapsed')"
        >
          <span aria-hidden="true">{{ collapsed ? '>' : '<' }}</span>
        </button>
      </div>

      <button class="new-chat-button" type="button" :title="copy.sidebar.newChat" @click="$emit('create-new-chat')">
        <span aria-hidden="true">+</span>
        <span class="new-chat-button__label">{{ copy.sidebar.newChat }}</span>
      </button>

      <section class="sidebar__section">
        <div class="sidebar__section-head">
          <span>{{ copy.sidebar.chats }}</span>
          <span class="sidebar__section-meta">
            <small>{{ sessions.length }}/{{ state.sessions.length }}</small>
            <button
              class="sidebar__clear-button"
              type="button"
              :disabled="!hasWebSessions(sessions)"
              :title="copy.sidebar.clearWebChats"
              @click="$emit('clear-web-sessions')"
            >
              {{ copy.sidebar.clearWebChatsShort }}
            </button>
          </span>
        </div>
        <div class="session-filter" role="group" :aria-label="copy.sidebar.chats">
          <button
            type="button"
            :aria-pressed="String(sessionChannelFilter === 'all')"
            @click="$emit('set-session-channel-filter', 'all')"
          >
            {{ copy.sidebar.filters.all }}
          </button>
          <button
            type="button"
            :aria-pressed="String(sessionChannelFilter === 'web')"
            @click="$emit('set-session-channel-filter', 'web')"
          >
            {{ copy.sidebar.filters.web }}
          </button>
        </div>
        <div class="session-list">
          <div
            v-for="session in sessions"
            :key="session.externalChatId"
            class="session-tile-wrap"
            :class="{ 'session-tile--active': session.externalChatId === state.activeExternalChatId }"
          >
            <button
              class="session-tile"
              type="button"
              :title="`${getSessionTitle(session)} · ${getSessionDisplayId(session)}`"
              @click="$emit('set-active-session', session.externalChatId)"
            >
              <span class="session-tile__initial" aria-hidden="true">{{ getSessionTitle(session).slice(0, 1) }}</span>
              <span class="session-tile__heading">
                <strong>{{ getSessionTitle(session) }}</strong>
                <span v-if="session.channel && session.channel !== 'web'" class="session-tile__channel">
                  {{ session.channel }} · read-only
                </span>
              </span>
              <span class="session-tile__id">{{ getSessionDisplayId(session) }}</span>
            </button>
            <button
              class="session-tile__delete"
              type="button"
              :title="copy.sidebar.deleteChat"
              :aria-label="copy.sidebar.deleteChat"
              @click.stop="$emit('delete-session', session)"
            >
              ×
            </button>
          </div>
        </div>
      </section>

    </div>

    <div class="sidebar__bottom">
      <BackgroundProcessSidebar
        :copy="copy"
        :processes="backgroundProcesses.processes"
        :loading="backgroundProcesses.loading"
        :error="backgroundProcesses.error"
        :collapsed="collapsed"
        :active-session-id="activeSessionId"
        @select-session="$emit('select-background-process', $event)"
        @select-run="$emit('select-background-process', $event)"
        @refresh="$emit('refresh-background-processes')"
      />

      <button class="settings-button" type="button" :title="copy.sidebar.settings" @click="$emit('open-settings')">
        <span class="settings-button__avatar" aria-hidden="true">OS</span>
        <span class="settings-button__copy">
          <strong>{{ copy.sidebar.settings }}</strong>
          <small>{{ copy.sidebar.settingsSubtitle }}</small>
        </span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import BackgroundProcessSidebar from "./BackgroundProcessSidebar.vue";

defineProps({
  copy: {
    type: Object,
    required: true,
  },
  state: {
    type: Object,
    required: true,
  },
  sessions: {
    type: Array,
    required: true,
  },
  sessionChannelFilter: {
    type: String,
    required: true,
  },
  collapsed: {
    type: Boolean,
    required: true,
  },
  backgroundProcesses: {
    type: Object,
    required: true,
  },
  activeSessionId: {
    type: String,
    default: "",
  },
  getSessionDisplayId: {
    type: Function,
    required: true,
  },
  getSessionTitle: {
    type: Function,
    required: true,
  },
});

function hasWebSessions(sessions) {
  return sessions.some((session) => !session.channel || session.channel === "web");
}

defineEmits([
  "create-new-chat",
  "delete-session",
  "clear-web-sessions",
  "set-active-session",
  "set-session-channel-filter",
  "select-background-process",
  "refresh-background-processes",
  "toggle-sidebar-collapsed",
  "open-settings",
]);
</script>
