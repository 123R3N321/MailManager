import { getProvider, listProviders } from "../llm/provider-registry.js";

describe("provider-registry", () => {
  test("getProvider returns dummy provider", () => {
    const p = getProvider("dummy");
    expect(p.id).toBe("dummy");
  });

  test("getProvider returns claude provider", () => {
    const p = getProvider("claude");
    expect(p.id).toBe("claude");
  });

  test("getProvider returns openai provider", () => {
    const p = getProvider("openai");
    expect(p.id).toBe("openai");
  });

  test("getProvider returns aws_backend provider", () => {
    const p = getProvider("aws_backend");
    expect(p.id).toBe("aws_backend");
  });

  test("getProvider throws on unknown id", () => {
    expect(() => getProvider("nonexistent")).toThrow();
  });

  test("listProviders returns all four providers", () => {
    const list = listProviders();
    const ids = list.map((p) => p.id);
    expect(ids).toContain("dummy");
    expect(ids).toContain("claude");
    expect(ids).toContain("openai");
    expect(ids).toContain("aws_backend");
  });

  test("all providers have required methods", () => {
    for (const { id } of listProviders()) {
      const p = getProvider(id);
      expect(typeof p.isConfigured).toBe("function");
      expect(typeof p.generateReply).toBe("function");
      expect(typeof p.getConfigFields).toBe("function");
      expect(typeof p.name).toBe("string");
    }
  });
});
