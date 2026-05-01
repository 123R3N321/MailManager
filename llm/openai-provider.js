export const openaiProvider = {
  name: "OpenAI",
  id: "openai",

  isConfigured(config) {
    return Boolean(config.apiKey && config.apiKey.trim().length > 0);
  },

  async generateReply(request, config) {
    const model = config.model || "gpt-4o-mini";
    const maxTokens = config.maxTokens || 512;
    const temperature = config.temperature ?? 0.7;

    const prompt = buildPrompt(request);

    const response = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${config.apiKey}`,
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
      throw Object.assign(new Error(`OpenAI API error ${response.status}: ${body}`), {
        code: "API_ERROR",
      });
    }

    const data = await response.json();
    const replyText = data.choices?.[0]?.message?.content;

    if (!replyText) {
      throw Object.assign(new Error("Unexpected response shape from OpenAI API"), {
        code: "INVALID_RESPONSE",
      });
    }

    return {
      replyText,
      providerId: "openai",
      modelUsed: model,
      truncated: data.choices?.[0]?.finish_reason === "length",
    };
  },

  getConfigFields() {
    return [
      {
        key: "apiKey",
        label: "OpenAI API Key",
        type: "password",
        placeholder: "sk-...",
        required: true,
      },
      {
        key: "model",
        label: "Model",
        type: "select",
        options: ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
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
