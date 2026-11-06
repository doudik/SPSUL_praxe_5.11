const PROVIDERS = {
  groq:    { baseURL: 'https://api.groq.com/openai/v1', envKey: 'GROQ_API_KEY' },
  mistral: { baseURL: 'https://api.mistral.ai/v1', envKey: 'MISTRAL_API_KEY' },
  gemini:  { baseURL: 'https://generativelanguage.googleapis.com/v1beta/openai/', envKey: 'GEMINI_API_KEY' },
  openrouter: { baseURL: 'https://openrouter.ai/api/v1', envKey: 'OPENROUTER_API_KEY' },
};

export function getProvider(name) {
  const p = PROVIDERS[name];
  if (!p) throw new Error(`Neznámý poskytovatel: ${name}`);
  return { ...p, apiKey: process.env[p.envKey] };
}