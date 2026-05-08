// Routes generation requests through our AWS Lambda + Bedrock RAG backend
// instead of calling an LLM API directly from the browser.
// The API URL comes from the Terraform `api_url` output after `terraform apply`.

export const awsBackendProvider = {
  name: "AWS Backend (RAG)",
  id: "aws-backend",

  isConfigured(config) {
    return Boolean(config.apiUrl && config.apiUrl.startsWith("https://"));
  },

  async generateReply(request, config) {
    const response = await fetch(`${config.apiUrl}/reply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        subject:       request.subject,
        senderName:    request.senderName,
        senderEmail:   request.senderEmail,
        bodyText:      request.bodyText,
        threadHistory: request.threadHistory || [],
        tone:          request.tone || "professional",
      }),
    });

    if (!response.ok) {
      const msg = await response.text().catch(() => "");
      throw Object.assign(
        new Error(`AWS backend error ${response.status}: ${msg}`),
        { code: "API_ERROR" }
      );
    }

    const data = await response.json();
    if (!data.replyText) {
      throw Object.assign(
        new Error("Unexpected response from AWS backend"),
        { code: "INVALID_RESPONSE" }
      );
    }

    return {
      replyText:      data.replyText,
      providerId:     "aws-backend",
      modelUsed:      data.modelUsed || "bedrock-claude",
      truncated:      data.truncated || false,
      retrievedCount: data.retrievedCount ?? 0,
    };
  },

  getConfigFields() {
    return [
      {
        key:         "apiUrl",
        label:       "API Gateway URL",
        type:        "text",
        placeholder: "https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com",
        required:    true,
      },
    ];
  },
};
