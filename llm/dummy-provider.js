// Dummy provider — returns realistic mock replies instantly, no API key required.
// Use this to verify the full extension pipeline before wiring up a real LLM.

const REPLIES = {
  professional: [
    "Thank you for reaching out, {name}. I have reviewed your message and will get back to you with a detailed response shortly. Please let me know if there is anything urgent in the meantime.",
    "Hi {name}, thank you for your email. I appreciate you taking the time to share this. I will review the details and follow up with you by end of week.",
    "Dear {name}, thank you for bringing this to my attention. I understand the importance of this matter and will prioritize it accordingly. I will send a comprehensive response once I have had a chance to review everything.",
  ],
  casual: [
    "Hey {name}! Thanks for the message — I'll take a look and get back to you soon.",
    "Hi {name}, got your email! Sounds good, let me check on this and ping you back.",
    "Hey {name}, thanks for reaching out! I'll get back to you shortly once I've had a chance to go through this.",
  ],
  brief: [
    "Hi {name}, thanks — will follow up shortly.",
    "Got it, {name}. I'll look into this and reply soon.",
    "Thanks {name}. On it.",
  ],
};

export const dummyProvider = {
  name: "Dummy (Test Mode)",
  id: "dummy",

  isConfigured(_config) {
    return true;
  },

  async generateReply(request, _config) {
    const tone = request.tone || "professional";
    const bank = REPLIES[tone] || REPLIES.professional;
    const template = bank[Math.floor(Math.random() * bank.length)];
    const replyText = template.replace("{name}", request.senderName || "there");

    return {
      replyText,
      providerId: "dummy",
      modelUsed: "dummy-v1",
      truncated: false,
    };
  },

  getConfigFields() {
    return [];
  },
};
