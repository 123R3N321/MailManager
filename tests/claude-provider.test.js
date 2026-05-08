import { claudeProvider } from "../llm/claude-provider.js";

const BASE_REQUEST = {
  subject: "Project update",
  senderName: "Bob",
  senderEmail: "bob@example.com",
  bodyText: "Just wanted to check in on the project status.",
  threadHistory: [],
  tone: "professional",
  language: "en",
};

const VALID_CONFIG = { apiKey: "sk-ant-test-key" };

// Capture fetch calls without making real network requests
let lastFetchArgs = null;
let mockFetchImpl = null;

global.fetch = async (...args) => {
  lastFetchArgs = args;
  return mockFetchImpl(...args);
};

function makeOkResponse(text) {
  return {
    ok: true,
    json: async () => ({
      content: [{ text }],
      stop_reason: "end_turn",
    }),
  };
}

function makeErrorResponse(status) {
  return {
    ok: false,
    status,
    text: async () => "Unauthorized",
  };
}

describe("claudeProvider", () => {
  test("id is 'claude'", () => {
    expect(claudeProvider.id).toBe("claude");
  });

  test("isConfigured is false without apiKey", () => {
    expect(claudeProvider.isConfigured({})).toBe(false);
    expect(claudeProvider.isConfigured({ apiKey: "" })).toBe(false);
    expect(claudeProvider.isConfigured({ apiKey: "   " })).toBe(false);
  });

  test("isConfigured is true with apiKey", () => {
    expect(claudeProvider.isConfigured({ apiKey: "sk-ant-abc" })).toBe(true);
  });

  test("calls Anthropic API with correct URL and headers", async () => {
    mockFetchImpl = async () => makeOkResponse("Hi Bob, thanks for reaching out.");
    await claudeProvider.generateReply(BASE_REQUEST, VALID_CONFIG);

    const [url, options] = lastFetchArgs;
    expect(url).toBe("https://api.anthropic.com/v1/messages");
    expect(options.headers["x-api-key"]).toBe("sk-ant-test-key");
    expect(options.headers["anthropic-version"]).toBeTruthy();
    expect(options.headers["Content-Type"]).toBe("application/json");
  });

  test("sends email context in the request body", async () => {
    mockFetchImpl = async () => makeOkResponse("Reply text here.");
    await claudeProvider.generateReply(BASE_REQUEST, VALID_CONFIG);

    const body = JSON.parse(lastFetchArgs[1].body);
    expect(body.messages[0].role).toBe("user");
    expect(body.messages[0].content).toContain("Bob");
    expect(body.messages[0].content).toContain("Project update");
  });

  test("returns correct shape on success", async () => {
    mockFetchImpl = async () => makeOkResponse("Thank you for the update, Bob.");
    const result = await claudeProvider.generateReply(BASE_REQUEST, VALID_CONFIG);

    expect(result.replyText).toBe("Thank you for the update, Bob.");
    expect(result.providerId).toBe("claude");
    expect(typeof result.modelUsed).toBe("string");
    expect(result.truncated).toBe(false);
  });

  test("sets truncated=true when stop_reason is max_tokens", async () => {
    mockFetchImpl = async () => ({
      ok: true,
      json: async () => ({ content: [{ text: "..." }], stop_reason: "max_tokens" }),
    });
    const result = await claudeProvider.generateReply(BASE_REQUEST, VALID_CONFIG);
    expect(result.truncated).toBe(true);
  });

  test("throws API_ERROR on non-ok response", async () => {
    mockFetchImpl = async () => makeErrorResponse(401);
    await expect(claudeProvider.generateReply(BASE_REQUEST, VALID_CONFIG)).rejects.toMatchObject({
      code: "API_ERROR",
    });
  });

  test("throws INVALID_RESPONSE on unexpected response shape", async () => {
    mockFetchImpl = async () => ({ ok: true, json: async () => ({}) });
    await expect(claudeProvider.generateReply(BASE_REQUEST, VALID_CONFIG)).rejects.toMatchObject({
      code: "INVALID_RESPONSE",
    });
  });

  test("uses model override from config", async () => {
    mockFetchImpl = async () => makeOkResponse("Reply.");
    await claudeProvider.generateReply(BASE_REQUEST, { ...VALID_CONFIG, model: "claude-opus-4-7" });

    const body = JSON.parse(lastFetchArgs[1].body);
    expect(body.model).toBe("claude-opus-4-7");
  });

  test("getConfigFields returns apiKey and model fields", () => {
    const fields = claudeProvider.getConfigFields();
    const keys = fields.map((f) => f.key);
    expect(keys).toContain("apiKey");
    expect(keys).toContain("model");
  });
});
