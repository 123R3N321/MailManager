import { dummyProvider } from "./dummy-provider.js";
import { claudeProvider } from "./claude-provider.js";
import { openaiProvider } from "./openai-provider.js";
import { awsBackendProvider } from "./aws-backend-provider.js";

const PROVIDERS = {
  [dummyProvider.id]:       dummyProvider,
  [claudeProvider.id]:      claudeProvider,
  [openaiProvider.id]:      openaiProvider,
  [awsBackendProvider.id]:  awsBackendProvider,
};

export function getProvider(id) {
  const provider = PROVIDERS[id];
  if (!provider) throw new Error(`Unknown provider: "${id}". Valid ids: ${Object.keys(PROVIDERS).join(", ")}`);
  return provider;
}

export function listProviders() {
  return Object.values(PROVIDERS).map(({ id, name }) => ({ id, name }));
}
