// Thin wrapper around chrome.storage.sync for typed get/set.

export async function getSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(
      {
        activeProviderId:   "dummy",
        tone:               "professional",
        language:           "en",
        claude_apiKey:      "",
        claude_model:       "claude-haiku-4-5-20251001",
        openai_apiKey:      "",
        openai_model:       "gpt-4o-mini",
        aws_backend_apiUrl: "",
        maxTokens:          512,
        temperature:        0.7,
      },
      resolve
    );
  });
}

export async function saveSettings(partial) {
  return new Promise((resolve, reject) => {
    chrome.storage.sync.set(partial, () => {
      if (chrome.runtime.lastError) reject(chrome.runtime.lastError);
      else resolve();
    });
  });
}

export function buildProviderConfig(settings, providerId) {
  return {
    apiKey:   settings[`${providerId}_apiKey`]   || "",
    model:    settings[`${providerId}_model`]    || "",
    apiUrl:   settings[`${providerId}_apiUrl`]   || "",
    maxTokens:   settings.maxTokens,
    temperature: settings.temperature,
  };
}
