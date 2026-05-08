import { awsBackendProvider } from "../llm/aws-backend-provider.js";

const BASE_REQUEST = {
  subject: "Project deadline",
  senderName: "Dana",
  senderEmail: "dana@example.com",
  bodyText: "Can we push the deadline by one day?",
  threadHistory: [],
  tone: "professional",
  language: "en",
};

const VALID_CONFIG = { apiUrl: "https://abc123.execute-api.us-east-1.amazonaws.com" };

let lastFetchArgs = null;
let mockFetchImpl = null;
global.fetch = async (...args) => { lastFetchArgs = args; return mockFetchImpl(...args); };

describe("awsBackendProvider", () => {
  test("id is 'aws-backend'", () => {
    expect(awsBackendProvider.id).toBe("aws-backend");
  });

  test("isConfigured requires an https apiUrl", () => {
    expect(awsBackendProvider.isConfigured({})).toBe(false);
    expect(awsBackendProvider.isConfigured({ apiUrl: "" })).toBe(false);
    expect(awsBackendProvider.isConfigured({ apiUrl: "http://not-https.com" })).toBe(false);
    expect(awsBackendProvider.isConfigured(VALID_CONFIG)).toBe(true);
  });

  test("calls POST /reply on the configured apiUrl", async () => {
    mockFetchImpl = async () => ({
      ok: true,
      json: async () => ({ replyText: "Sure, one day extension is fine.", modelUsed: "claude-haiku", retrievedCount: 2 }),
    });

    await awsBackendProvider.generateReply(BASE_REQUEST, VALID_CONFIG);

    const [url, opts] = lastFetchArgs;
    expect(url).toBe("https://abc123.execute-api.us-east-1.amazonaws.com/reply");
    expect(opts.method).toBe("POST");
    expect(opts.headers["Content-Type"]).toBe("application/json");
  });

  test("sends correct fields in the request body", async () => {
    mockFetchImpl = async () => ({
      ok: true,
      json: async () => ({ replyText: "Reply.", modelUsed: "claude-haiku", retrievedCount: 0 }),
    });

    await awsBackendProvider.generateReply(BASE_REQUEST, VALID_CONFIG);
    const body = JSON.parse(lastFetchArgs[1].body);

    expect(body.subject).toBe("Project deadline");
    expect(body.senderName).toBe("Dana");
    expect(body.senderEmail).toBe("dana@example.com");
    expect(body.bodyText).toBeDefined();
    expect(Array.isArray(body.threadHistory)).toBe(true);
  });

  test("returns correct shape on success", async () => {
    mockFetchImpl = async () => ({
      ok: true,
      json: async () => ({ replyText: "No problem, Dana.", modelUsed: "claude-haiku", retrievedCount: 3, truncated: false }),
    });

    const result = await awsBackendProvider.generateReply(BASE_REQUEST, VALID_CONFIG);
    expect(result.replyText).toBe("No problem, Dana.");
    expect(result.providerId).toBe("aws-backend");
    expect(result.modelUsed).toBe("claude-haiku");
    expect(result.retrievedCount).toBe(3);
  });

  test("throws API_ERROR on non-ok response", async () => {
    mockFetchImpl = async () => ({ ok: false, status: 500, text: async () => "Internal error" });
    await expect(awsBackendProvider.generateReply(BASE_REQUEST, VALID_CONFIG)).rejects.toMatchObject({
      code: "API_ERROR",
    });
  });

  test("throws INVALID_RESPONSE when replyText is missing", async () => {
    mockFetchImpl = async () => ({ ok: true, json: async () => ({ error: "Something went wrong" }) });
    await expect(awsBackendProvider.generateReply(BASE_REQUEST, VALID_CONFIG)).rejects.toMatchObject({
      code: "INVALID_RESPONSE",
    });
  });

  test("getConfigFields returns apiUrl field", () => {
    const fields = awsBackendProvider.getConfigFields();
    expect(fields.map(f => f.key)).toContain("apiUrl");
  });
});
