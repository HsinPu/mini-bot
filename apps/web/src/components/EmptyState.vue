<template>
  <section class="empty-state" aria-label="Start a chat">
    <div class="empty-state__mark" aria-hidden="true">OS</div>
    <h1>How can OpenSprite help?</h1>
    <p>Start a local conversation. The page connects to your gateway automatically.</p>
    <div class="prompt-grid">
      <button
        v-for="prompt in prompts"
        :key="prompt.title"
        class="prompt-card"
        type="button"
        @click="$emit('apply-prompt', prompt.text)"
      >
        <strong>{{ prompt.title }}</strong>
        <span>{{ prompt.description }}</span>
      </button>
    </div>
  </section>
</template>

<script setup>
defineProps({
  prompts: {
    type: Array,
    required: true,
  },
});

defineEmits(["apply-prompt"]);
</script>
