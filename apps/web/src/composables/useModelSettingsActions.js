import { normalizeMediaSettings, normalizeOpenRouterOptions } from "./settingsNormalizers";

export function useModelSettingsActions({ settingsState, requestSettingsJson, copy, setSettingsSuccess }) {
  async function loadModelSettings() {
    settingsState.modelsLoading = true;
    settingsState.mediaLoading = true;
    settingsState.llmLoading = true;
    settingsState.modelsError = "";
    settingsState.mediaError = "";
    settingsState.llmError = "";
    try {
      const [models, media, llm] = await Promise.all([
        requestSettingsJson("/api/settings/models"),
        requestSettingsJson("/api/settings/media"),
        requestSettingsJson("/api/settings/llm"),
      ]);
      settingsState.models = models;
      settingsState.media = normalizeMediaSettings(media);
      settingsState.llm = {
        pass_decoding_params: Boolean(llm?.llm?.pass_decoding_params),
      };
      if (
        !settingsState.selectedTextProviderId ||
        !(settingsState.models.providers || []).some((provider) => provider.id === settingsState.selectedTextProviderId)
      ) {
        const activeProvider = (settingsState.models.providers || []).find((provider) => provider.is_default);
        settingsState.selectedTextProviderId = activeProvider?.id || settingsState.models.providers?.[0]?.id || "";
      }
      for (const provider of settingsState.models.providers || []) {
        const selectedModel = provider.selected_model || provider.models?.[0] || "";
        settingsState.modelSelections[provider.id] = selectedModel;
        if (!Object.prototype.hasOwnProperty.call(settingsState.customModels, provider.id)) {
          settingsState.customModels[provider.id] = "";
        }
        if (provider.provider === "openrouter") {
          settingsState.openRouterOptions[provider.id] = normalizeOpenRouterOptions(provider.options || {});
        }
      }
      for (const category of Object.keys(settingsState.media.sections || {})) {
        const section = settingsState.media.sections[category] || {};
        settingsState.mediaSelections[category] = {
          enabled: Boolean(section.enabled),
          providerId: section.provider_id || settingsState.media.providers?.[0]?.id || "",
          model: section.model || "",
        };
        if (!Object.prototype.hasOwnProperty.call(settingsState.mediaCustomModels, category)) {
          settingsState.mediaCustomModels[category] = "";
        }
      }
    } catch (error) {
      settingsState.modelsError = error?.message || copy.value.notices.modelLoadFailed;
      settingsState.mediaError = error?.message || copy.value.notices.mediaModelLoadFailed;
      settingsState.llmError = error?.message || copy.value.notices.llmSettingsLoadFailed;
    } finally {
      settingsState.modelsLoading = false;
      settingsState.mediaLoading = false;
      settingsState.llmLoading = false;
    }
  }

  async function saveLlmSettings() {
    settingsState.llmLoading = true;
    settingsState.llmError = "";
    settingsState.llmNotice = "";
    try {
      const payload = await requestSettingsJson("/api/settings/llm", {
        method: "PUT",
        body: JSON.stringify({
          pass_decoding_params: Boolean(settingsState.llm.pass_decoding_params),
        }),
      });
      settingsState.llm = {
        pass_decoding_params: Boolean(payload?.llm?.pass_decoding_params),
      };
      setSettingsSuccess(
        "llmNotice",
        payload.restart_required ? copy.value.notices.modelRestartRequired : copy.value.notices.llmSettingsSaved,
      );
    } catch (error) {
      settingsState.llmError = error?.message || copy.value.notices.llmSettingsSaveFailed;
    } finally {
      settingsState.llmLoading = false;
    }
  }

  async function saveMediaModel(category, modelOverride = "") {
    const selection = settingsState.mediaSelections[category] || {};
    const normalizedModel = String(modelOverride || selection.model || "").trim();
    if (selection.enabled && !normalizedModel) {
      settingsState.mediaError = copy.value.notices.modelRequired;
      return;
    }
    settingsState.mediaLoading = true;
    settingsState.mediaError = "";
    settingsState.mediaNotice = "";
    try {
      const payload = await requestSettingsJson("/api/settings/media", {
        method: "PUT",
        body: JSON.stringify({
          category,
          enabled: Boolean(selection.enabled),
          provider_id: selection.providerId,
          model: normalizedModel,
        }),
      });
      settingsState.media = normalizeMediaSettings(payload.media);
      settingsState.mediaSelections[category] = {
        enabled: Boolean(settingsState.media.sections[category]?.enabled),
        providerId: settingsState.media.sections[category]?.provider_id || selection.providerId || "",
        model: settingsState.media.sections[category]?.model || normalizedModel,
      };
      settingsState.mediaCustomModels[category] = "";
      setSettingsSuccess(
        "mediaNotice",
        payload.restart_required ? copy.value.notices.mediaModelRestartRequired : copy.value.notices.mediaModelApplied,
      );
    } catch (error) {
      settingsState.mediaError = error?.message || copy.value.notices.mediaModelSaveFailed;
    } finally {
      settingsState.mediaLoading = false;
    }
  }

  return {
    loadModelSettings,
    saveLlmSettings,
    saveMediaModel,
  };
}
