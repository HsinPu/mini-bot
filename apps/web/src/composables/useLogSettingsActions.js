const DEFAULT_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"];

function normalizeLogSettings(log = {}) {
  const levels = Array.isArray(log.levels) && log.levels.length
    ? log.levels.map((level) => String(level || "").toUpperCase()).filter(Boolean)
    : DEFAULT_LOG_LEVELS;
  const level = String(log.level || "INFO").toUpperCase();
  return {
    enabled: Boolean(log.enabled),
    level: levels.includes(level) ? level : "INFO",
    retention_days: Number(log.retention_days || 365),
    log_system_prompt: log.log_system_prompt !== false,
    log_system_prompt_lines: Number(log.log_system_prompt_lines || 0),
    log_reasoning_details: Boolean(log.log_reasoning_details),
    levels,
  };
}

function syncLogForm(settingsState) {
  settingsState.logForm.enabled = Boolean(settingsState.log.enabled);
  settingsState.logForm.level = settingsState.log.level || "INFO";
  settingsState.logForm.retentionDays = Number(settingsState.log.retention_days || 365);
  settingsState.logForm.logSystemPrompt = Boolean(settingsState.log.log_system_prompt);
  settingsState.logForm.logSystemPromptLines = Number(settingsState.log.log_system_prompt_lines || 0);
  settingsState.logForm.logReasoningDetails = Boolean(settingsState.log.log_reasoning_details);
}

export function useLogSettingsActions({ settingsState, requestSettingsJson, copy, setSettingsSuccess }) {
  async function loadLogSettings() {
    settingsState.logLoading = true;
    settingsState.logError = "";
    try {
      const payload = await requestSettingsJson("/api/settings/log");
      settingsState.log = normalizeLogSettings(payload.log || {});
      syncLogForm(settingsState);
    } catch (error) {
      settingsState.logError = error?.message || copy.value.notices.logLoadFailed;
    } finally {
      settingsState.logLoading = false;
    }
  }

  async function saveLogSettings() {
    settingsState.logLoading = true;
    settingsState.logError = "";
    settingsState.logNotice = "";
    try {
      const payload = await requestSettingsJson("/api/settings/log", {
        method: "PUT",
        body: JSON.stringify({
          enabled: Boolean(settingsState.logForm.enabled),
          level: settingsState.logForm.level || "INFO",
          retention_days: Number(settingsState.logForm.retentionDays || 365),
          log_system_prompt: Boolean(settingsState.logForm.logSystemPrompt),
          log_system_prompt_lines: Number(settingsState.logForm.logSystemPromptLines || 0),
          log_reasoning_details: Boolean(settingsState.logForm.logReasoningDetails),
        }),
      });
      settingsState.log = normalizeLogSettings(payload.log || {});
      syncLogForm(settingsState);
      setSettingsSuccess("logNotice", copy.value.notices.logSaved);
    } catch (error) {
      settingsState.logError = error?.message || copy.value.notices.logSaveFailed;
    } finally {
      settingsState.logLoading = false;
    }
  }

  return {
    loadLogSettings,
    saveLogSettings,
  };
}
