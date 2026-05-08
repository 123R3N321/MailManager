import { getSettings, saveSettings } from "./utils/storage.js";

async function init() {
  const settings = await getSettings();

  const storedProvider = settings.activeProviderId === "aws-backend" ? "aws_backend" : settings.activeProviderId;
  document.getElementById("provider-select").value = storedProvider;
  document.getElementById("aws-api-url").value = settings.aws_backend_apiUrl || "";
  document.getElementById("claude-key").value = settings.claude_apiKey || "";
  document.getElementById("claude-model").value = settings.claude_model;
  document.getElementById("openai-key").value = settings.openai_apiKey || "";
  document.getElementById("openai-model").value = settings.openai_model;
  document.getElementById("tone-select").value = settings.tone;
  document.getElementById("language-input").value = settings.language;

  updateSectionVisibility(settings.activeProviderId);

  document.getElementById("provider-select").addEventListener("change", (e) => {
    updateSectionVisibility(e.target.value);
  });

  document.getElementById("settings-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    await saveSettings({
      activeProviderId:   document.getElementById("provider-select").value,
      aws_backend_apiUrl: document.getElementById("aws-api-url").value.trim(),
      claude_apiKey:      document.getElementById("claude-key").value.trim(),
      claude_model:       document.getElementById("claude-model").value,
      openai_apiKey:      document.getElementById("openai-key").value.trim(),
      openai_model:       document.getElementById("openai-model").value,
      tone:               document.getElementById("tone-select").value,
      language:           document.getElementById("language-input").value.trim() || "en",
    });

    const msg = document.getElementById("save-msg");
    msg.textContent = "Saved!";
    setTimeout(() => (msg.textContent = ""), 2000);
  });
}

function updateSectionVisibility(providerId) {
  document.getElementById("aws_backend-section").style.display =
    providerId === "aws_backend" ? "block" : "none";
  document.getElementById("claude-section").style.display =
    providerId === "claude" ? "block" : "none";
  document.getElementById("openai-section").style.display =
    providerId === "openai" ? "block" : "none";
}

init();
