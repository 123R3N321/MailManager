import { getProvider, listProviders } from "./llm/provider-registry.js";
import { getSettings, saveSettings, buildProviderConfig } from "./utils/storage.js";

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  handleMessage(message).then(sendResponse).catch((err) => {
    sendResponse({ success: false, error: { code: "NETWORK_ERROR", message: err.message, providerId: "unknown" } });
  });
  return true; // keep channel open for async response
});

async function handleMessage(message) {
  switch (message.type) {
    case "GENERATE_REPLY":
      return handleGenerateReply(message.payload);

    case "GET_STATUS":
      return handleGetStatus();

    case "SET_PROVIDER":
      await saveSettings({ activeProviderId: message.payload.providerId });
      return { success: true };

    case "LIST_PROVIDERS":
      return { success: true, data: listProviders() };

    default:
      return { success: false, error: { code: "UNKNOWN_MESSAGE", message: `Unknown message type: ${message.type}` } };
  }
}

async function handleGenerateReply(payload) {
  const settings = await getSettings();
  const providerId = settings.activeProviderId;
  let provider;

  try {
    provider = getProvider(providerId);
  } catch (err) {
    return { success: false, error: { code: "NOT_CONFIGURED", message: err.message, providerId } };
  }

  const config = buildProviderConfig(settings, providerId);

  if (!provider.isConfigured(config)) {
    return {
      success: false,
      error: {
        code: "NOT_CONFIGURED",
        message: `${provider.name} is not configured. Open the extension options to set it up.`,
        providerId,
      },
    };
  }

  const request = {
    subject: payload.subject || "(no subject)",
    senderName: payload.senderName || "Unknown",
    senderEmail: payload.senderEmail || "",
    bodyText: payload.bodyText || "",
    threadHistory: payload.threadHistory || [],
    tone: settings.tone,
    language: settings.language,
  };

  try {
    const result = await provider.generateReply(request, config);
    return { success: true, data: result };
  } catch (err) {
    return {
      success: false,
      error: {
        code: err.code || "API_ERROR",
        message: err.message,
        providerId,
      },
    };
  }
}

async function handleGetStatus() {
  const settings = await getSettings();
  const providerId = settings.activeProviderId;
  let isConfigured = false;

  try {
    const provider = getProvider(providerId);
    isConfigured = provider.isConfigured(buildProviderConfig(settings, providerId));
  } catch (_) {}

  return { success: true, data: { activeProvider: providerId, isConfigured } };
}
