<template>
  <form class="composer" @submit="$emit('submit', $event)">
    <label class="sr-only" for="messageInput">Message</label>
    <div class="composer__box">
      <textarea
        id="messageInput"
        :ref="setInputRef"
        :value="modelValue"
        rows="1"
        placeholder="Message OpenSprite"
        autocomplete="off"
        @input="handleInput"
        @keydown="$emit('keydown', $event)"
      ></textarea>
      <button class="send-button" type="submit" aria-label="Send message" :disabled="disabled">
        Send
      </button>
    </div>
    <div class="composer__footer">
      <span>OpenSprite can make mistakes. Check important work.</span>
      <span>{{ runtimeHint }}</span>
    </div>
  </form>
</template>

<script setup>
defineProps({
  modelValue: {
    type: String,
    required: true,
  },
  disabled: {
    type: Boolean,
    required: true,
  },
  runtimeHint: {
    type: String,
    required: true,
  },
  setInputRef: {
    type: Function,
    required: true,
  },
});

const emit = defineEmits(["update:modelValue", "input", "keydown", "submit"]);

function handleInput(event) {
  emit("update:modelValue", event.target.value);
  emit("input", event);
}
</script>
