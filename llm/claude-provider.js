export const claudeProvider = {
  name: "Claude (Anthropic)",
  id: "claude",

  isConfigured(config) {
    return Boolean(config.apiKey && config.apiKey.trim().length > 0);
  },

  async generateReply(request, config) {
    const model = config.model || "claude-haiku-4-5-20251001";
    const maxTokens = config.maxTokens || 512;
    const temperature = config.temperature ?? 0.7;

    const prompt = buildPrompt(request);

    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": config.apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model,
        max_tokens: maxTokens,
        temperature,
        messages: [{ role: "user", content: prompt }],
      }),
    });

    if (!response.ok) {
      const body = await response.text().catch(() => "");
      throw Object.assign(new Error(`Anthropic API error ${response.status}: ${body}`), {
        code: "API_ERROR",
      });
    }

    const data = await response.json();
    const replyText = data.content?.[0]?.text;

    if (!replyText) {
      throw Object.assign(new Error("Unexpected response shape from Anthropic API"), {
        code: "INVALID_RESPONSE",
      });
    }

    return {
      replyText,
      providerId: "claude",
      modelUsed: model,
      truncated: data.stop_reason === "max_tokens",
    };
  },

  getConfigFields() {
    return [
      {
        key: "apiKey",
        label: "Anthropic API Key",
        type: "password",
        placeholder: "sk-ant-...",
        required: true,
      },
      {
        key: "model",
        label: "Model",
        type: "select",
        options: [
          "claude-haiku-4-5-20251001",
          "claude-sonnet-4-6",
          "claude-opus-4-7",
        ],
        required: false,
      },
    ];
  },
};

function buildPrompt(request) {
  const toneInstruction = {
    professional: "Write a professional and polished reply.",
    casual: "Write a friendly and casual reply.",
    brief: "Write a very short and direct reply (2-3 sentences max).",
  }[request.tone] || "Write a professional reply.";

  const historySection = request.threadHistory?.length
    ? `\n\nEarlier messages in this thread (oldest first):\n${request.threadHistory.map((m, i) => `[${i + 1}] ${m}`).join("\n\n")}\n`
    : "";

  return `You are drafting an email reply on behalf of the user.${historySection}

Email to reply to:
From: ${request.senderName} <${request.senderEmail}>
Subject: ${request.subject}

${request.bodyText}

---
${toneInstruction} Reply in ${request.language || "English"}. Output only the reply text, no subject line, no greeting label.`;
}
