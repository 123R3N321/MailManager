import { dummyProvider } from "../llm/dummy-provider.js";

const BASE_REQUEST = {
  subject: "Meeting tomorrow",
  senderName: "Alice",
  senderEmail: "alice@example.com",
  bodyText: "Can we reschedule our meeting to 3pm?",
  threadHistory: [],
  tone: "professional",
  language: "en",
};

describe("dummyProvider", () => {
  test("id and name are set", () => {
    expect(dummyProvider.id).toBe("dummy");
    expect(typeof dummyProvider.name).toBe("string");
  });

  test("isConfigured always returns true", () => {
    expect(dummyProvider.isConfigured({})).toBe(true);
    expect(dummyProvider.isConfigured({ apiKey: "" })).toBe(true);
  });

  test("generateReply returns correct shape", async () => {
    const result = await dummyProvider.generateReply(BASE_REQUEST, {});
    expect(typeof result.replyText).toBe("string");
    expect(result.replyText.length).toBeGreaterThan(0);
    expect(result.providerId).toBe("dummy");
    expect(result.modelUsed).toBe("dummy-v1");
    expect(result.truncated).toBe(false);
  });

  test("reply interpolates sender name", async () => {
    const result = await dummyProvider.generateReply(BASE_REQUEST, {});
    expect(result.replyText).toContain("Alice");
  });

  test("casual tone returns a reply", async () => {
    const result = await dummyProvider.generateReply({ ...BASE_REQUEST, tone: "casual" }, {});
    expect(result.replyText.length).toBeGreaterThan(0);
  });

  test("brief tone returns a reply", async () => {
    const result = await dummyProvider.generateReply({ ...BASE_REQUEST, tone: "brief" }, {});
    expect(result.replyText.length).toBeGreaterThan(0);
  });

  test("unknown tone falls back gracefully", async () => {
    const result = await dummyProvider.generateReply({ ...BASE_REQUEST, tone: "nonexistent" }, {});
    expect(result.replyText.length).toBeGreaterThan(0);
  });

  test("missing senderName uses fallback", async () => {
    const result = await dummyProvider.generateReply({ ...BASE_REQUEST, senderName: "" }, {});
    expect(result.replyText).toContain("there");
  });

  test("getConfigFields returns empty array", () => {
    expect(dummyProvider.getConfigFields()).toEqual([]);
  });
});
