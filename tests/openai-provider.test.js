import { openaiProvider } from "../llm/openai-provider.js";

const BASE_REQUEST = {
  subject: "Quick question",
  senderName: "Carol",
  senderEmail: "carol@example.com",
  bodyText: "Do you have time for a call this week?",
  threadHistory: [],
  tone: "casual",
  language: "en",
};

const VALID_CONFIG = { apiKey: "sk-openai-test-key" };

let lastFetchArgs = null;
let mockFetchImpl = null;

global.fetch = async (...args) => {
  lastFetchArgs = args;
  return mockFetchImpl(...args);
};

function makeOkResponse(content) {
  return {
    ok: true,
    json: async () => ({
      choices: [{ message: { content }, finish_reason: "stop" }],
    }),
  };
}

describe("openaiProvider", () => {
  test("id is 'openai'", () => {
    expect(openaiProvider.id).toBe("openai");
  });

  test("isConfigured requires non-empty apiKey", () => {
    expect(openaiProvider.isConfigured({})).toBe(false);
    expect(openaiProvider.isConfigured({ apiKey: "sk-abc" })).toBe(true);
  });

  test("calls OpenAI API with correct URL and Authorization header", async () => {
    mockFetchImpl = async () => makeOkResponse("Sure, let's find a time!");
    await openaiProvider.generateReply(BASE_REQUEST, VALID_CONFIG);

    const [url, options] = lastFetchArgs;
    expect(url).toBe("https://api.openai.com/v1/chat/completions");
    expect(options.headers["Authorization"]).toBe("Bearer sk-openai-test-key");
  });

  test("returns correct shape on success", async () => {
    mockFetchImpl = async () => makeOkResponse("Sounds great, Carol!");
    const result = await openaiProvider.generateReply(BASE_REQUEST, VALID_CONFIG);

    expect(result.replyText).toBe("Sounds great, Carol!");
    expect(result.providerId).toBe("openai");
    expect(typeof result.modelUsed).toBe("string");
    expect(result.truncated).toBe(false);
  });

  test("sets truncated=true on finish_reason=length", async () => {
    mockFetchImpl = async () => ({
      ok: true,
      json: async () => ({ choices: [{ message: { content: "..." }, finish_reason: "length" }] }),
    });
    const result = await openaiProvider.generateReply(BASE_REQUEST, VALID_CONFIG);
    expect(result.truncated).toBe(true);
  });

  test("throws API_ERROR on non-ok response", async () => {
    mockFetchImpl = async () => ({ ok: false, status: 429, text: async () => "Rate limited" });
    await expect(openaiProvider.generateReply(BASE_REQUEST, VALID_CONFIG)).rejects.toMatchObject({
      code: "API_ERROR",
    });
  });

  test("throws INVALID_RESPONSE on empty choices", async () => {
    mockFetchImpl = async () => ({ ok: true, json: async () => ({ choices: [] }) });
    await expect(openaiProvider.generateReply(BASE_REQUEST, VALID_CONFIG)).rejects.toMatchObject({
      code: "INVALID_RESPONSE",
    });
  });
});
