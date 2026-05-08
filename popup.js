const PROVIDER_LABELS = {
  dummy:        "Dummy (Test)",
  claude:       "Claude",
  openai:       "OpenAI",
  "aws-backend": "AWS Backend (RAG)",
};

async function init() {
  const response = await chrome.runtime.sendMessage({ type: "GET_STATUS" });

  if (response?.success) {
    const { activeProvider, isConfigured } = response.data;
    document.getElementById("provider-name").textContent =
      PROVIDER_LABELS[activeProvider] || activeProvider;

    const badge = document.getElementById("status-badge");
    badge.textContent = isConfigured ? "Ready" : "Not configured";
    badge.className = "badge " + (isConfigured ? "badge-ok" : "badge-warn");
  }

  document.getElementById("options-link").addEventListener("click", (e) => {
    e.preventDefault();
    chrome.runtime.openOptionsPage();
  });
}

init();
