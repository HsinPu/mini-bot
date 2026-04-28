<template>
  <div v-if="open" class="settings-modal">
    <button
      class="settings-modal__backdrop"
      type="button"
      aria-label="Close settings"
      @click="$emit('close')"
    ></button>

    <section class="settings-panel" role="dialog" aria-modal="true" aria-labelledby="settingsTitle">
      <aside class="settings-nav" aria-label="Settings sections">
        <div class="settings-nav__group">
          <p>桌面</p>
          <button
            class="settings-nav__item"
            :class="{ 'settings-nav__item--active': section === 'general' }"
            type="button"
            @click="$emit('select-section', 'general')"
          >
            <span aria-hidden="true">⌘</span>
            一般
          </button>
          <button
            class="settings-nav__item"
            :class="{ 'settings-nav__item--active': section === 'shortcuts' }"
            type="button"
            @click="$emit('select-section', 'shortcuts')"
          >
            <span aria-hidden="true">⌗</span>
            快速鍵
          </button>
        </div>

        <div class="settings-nav__group">
          <p>伺服器</p>
          <button
            class="settings-nav__item"
            :class="{ 'settings-nav__item--active': section === 'providers' }"
            type="button"
            @click="$emit('select-section', 'providers')"
          >
            <span aria-hidden="true">⚙</span>
            提供者
          </button>
          <button
            class="settings-nav__item"
            :class="{ 'settings-nav__item--active': section === 'models' }"
            type="button"
            @click="$emit('select-section', 'models')"
          >
            <span aria-hidden="true">✦</span>
            模型
          </button>
        </div>

        <div class="settings-nav__footer">
          <strong>OpenSprite Web</strong>
          <span>v0.1.0</span>
        </div>
      </aside>

      <div class="settings-content">
        <header class="settings-content__header">
          <h2 id="settingsTitle">{{ title }}</h2>
          <button class="settings-panel__close" type="button" aria-label="Close settings" @click="$emit('close')">
            Close
          </button>
        </header>

        <section v-show="section === 'general'" class="settings-page">
          <div class="settings-card">
            <div class="settings-row">
              <div>
                <strong>語言</strong>
                <span>變更 OpenSprite 的顯示語言</span>
              </div>
              <select aria-label="Language">
                <option>繁體中文</option>
                <option>English</option>
              </select>
            </div>

            <label class="settings-row">
              <div>
                <strong>自動接受權限</strong>
                <span>權限請求將被自動批准</span>
              </div>
              <input class="switch" type="checkbox" />
            </label>

            <label class="settings-row">
              <div>
                <strong>顯示推理摘要</strong>
                <span>在時間軸中顯示模型推理摘要</span>
              </div>
              <input class="switch" type="checkbox" />
            </label>

            <label class="settings-row">
              <div>
                <strong>展開 shell 工具區塊</strong>
                <span>在時間軸中預設展開 shell 工具區塊</span>
              </div>
              <input class="switch" type="checkbox" />
            </label>

            <label class="settings-row">
              <div>
                <strong>展開 edit 工具區塊</strong>
                <span>在時間軸中預設展開 edit、write 和 patch 工具區塊</span>
              </div>
              <input class="switch" type="checkbox" />
            </label>

            <label class="settings-row">
              <div>
                <strong>顯示工作階段進度列</strong>
                <span>當代理程式正在運作時，在工作階段頂部顯示動畫進度列</span>
              </div>
              <input class="switch" type="checkbox" checked />
            </label>
          </div>

          <h3>連線</h3>
          <div class="settings-card settings-card--form">
            <label class="settings-row settings-row--field">
              <div>
                <strong>WebSocket URL</strong>
                <span>OpenSprite gateway 的連線位置</span>
              </div>
              <input v-model="form.wsUrl" type="text" spellcheck="false" />
            </label>

            <label class="settings-row settings-row--field">
              <div>
                <strong>Display name</strong>
                <span>送出訊息時顯示的使用者名稱</span>
              </div>
              <input v-model="form.displayName" type="text" maxlength="60" />
            </label>

            <label class="settings-row settings-row--field">
              <div>
                <strong>Chat ID</strong>
                <span>用固定 ID 將瀏覽器分頁綁定到同一個 session</span>
              </div>
              <input v-model="form.chatId" type="text" spellcheck="false" />
            </label>

            <div class="settings-panel__actions">
              <button class="primary-button" type="button" @click="$emit('save')">Save and connect</button>
              <button class="secondary-button" type="button" @click="$emit('disconnect')">Disconnect</button>
            </div>
          </div>

          <h3>外觀</h3>
          <div class="settings-card">
            <div class="settings-row">
              <div>
                <strong>配色方案</strong>
                <span>選擇 OpenSprite 要跟隨系統、淺色或深色主題</span>
              </div>
              <select aria-label="Color scheme">
                <option>系統</option>
                <option>淺色</option>
                <option>深色</option>
              </select>
            </div>
          </div>
        </section>

        <section v-show="section === 'shortcuts'" class="settings-page">
          <div class="settings-card">
            <div class="settings-row">
              <div>
                <strong>開啟設定</strong>
                <span>快速開啟這個設定視窗</span>
              </div>
              <div class="shortcut-keys"><kbd>Ctrl</kbd><kbd>,</kbd></div>
            </div>
            <div class="settings-row">
              <div>
                <strong>送出訊息</strong>
                <span>在輸入框中送出目前訊息</span>
              </div>
              <div class="shortcut-keys"><kbd>Enter</kbd></div>
            </div>
          </div>
        </section>

        <section v-show="section === 'providers'" class="settings-page">
          <div class="settings-card">
            <div class="settings-row">
              <div>
                <strong>提供者設定</strong>
                <span>提供者設定之後會放在這裡</span>
              </div>
              <span class="settings-muted">Coming soon</span>
            </div>
          </div>
        </section>

        <section v-show="section === 'models'" class="settings-page">
          <div class="settings-card">
            <div class="settings-row">
              <div>
                <strong>模型設定</strong>
                <span>模型清單與預設模型之後會放在這裡</span>
              </div>
              <span class="settings-muted">Coming soon</span>
            </div>
          </div>
        </section>
      </div>
    </section>
  </div>
</template>

<script setup>
defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  section: {
    type: String,
    required: true,
  },
  title: {
    type: String,
    required: true,
  },
  form: {
    type: Object,
    required: true,
  },
});

defineEmits(["close", "select-section", "save", "disconnect"]);
</script>
