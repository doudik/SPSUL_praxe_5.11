import 'dotenv/config';
import fs from 'node:fs';
import { getProvider } from './providers.js';
import { compareCase } from './compare.js';
import { cacheGet, cacheSet } from './cache.js';

function parseArgs() {
  const args = Object.fromEntries(
    process.argv.slice(2).map(a => a.replace(/^--/, '').split('='))
  );
  return {
    model: args.model,
    provider: args.provider,
    sada: args.sada ?? 'dev',
    prompt: args.prompt ?? 'v1',
  };
}

function loadCases(sada) {
  const path = `data/${sada}.jsonl`;
  return fs.readFileSync(path, 'utf-8')
    .split('\n')
    .filter(l => l.trim())
    .map(l => JSON.parse(l));
}

function loadPrompt(prompt) {
  return fs.readFileSync(`prompts/${prompt}.txt`, 'utf-8');
}

function round(n) {
  return Math.round(n * 1000) / 1000;
}

async function callModel({ baseURL, apiKey, model, systemPrompt, input, maxRetries = 5 }) {
  const body = {
    model,
    temperature: 0,
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: input },
    ],
  };

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const start = Date.now();
    const res = await fetch(`${baseURL}/chat/completions`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (res.status === 429) {
      const waitMs = 15000;
      console.log(`  429 rate limit, čekám ${waitMs / 1000}s a zkouším znovu (pokus ${attempt + 1}/${maxRetries})...`);
      await new Promise(r => setTimeout(r, waitMs));
      continue;
    }

    if (!res.ok) {
      throw new Error(`API chyba ${res.status}: ${await res.text()}`);
    }

    const data = await res.json();
    return {
      content: data.choices[0].message.content,
      promptTokens: data.usage?.prompt_tokens ?? 0,
      completionTokens: data.usage?.completion_tokens ?? 0,
      latencyMs: Date.now() - start,
    };
  }

  throw new Error('Vyčerpány všechny pokusy po opakovaných 429 chybách.');
}

function extractJson(raw) {
  // model někdy obalí JSON do ```json ... ``` bloku, i když je o to v promptu požádán, aby nedělal
  const match = raw.match(/\{[\s\S]*\}/);
  if (!match) return null;
  try {
    return JSON.parse(match[0]);
  } catch {
    return null;
  }
}

async function main() {
  const { model, provider, sada, prompt: promptName } = parseArgs();
  if (!model || !provider) {
    console.error('Použití: node src/run-eval.js --model=... --provider=... --sada=dev --prompt=v1');
    process.exit(1);
  }

  const cases = loadCases(sada);
  const systemPrompt = loadPrompt(promptName);
  const { baseURL, apiKey } = getProvider(provider);
  if (!apiKey) throw new Error(`Chybí API klíč pro poskytovatele "${provider}" v .env`);

  const fieldHits = {};
  let validJsonCount = 0;
  let fullMatchCount = 0;
  let totalPromptTokens = 0;
  let totalCompletionTokens = 0;
  const latencies = [];
  const rawResponses = [];

  for (const c of cases) {
    let result = cacheGet(model, promptName, c.input);
    if (result) {
      console.log(`[${c.id}] z cache`);
    } else {
      console.log(`[${c.id}] volám ${model} přes ${provider}...`);
      result = await callModel({ baseURL, apiKey, model, systemPrompt, input: c.input });
      cacheSet(model, promptName, c.input, result);
    }

    rawResponses.push({ id: c.id, raw: result.content });
    totalPromptTokens += result.promptTokens;
    totalCompletionTokens += result.completionTokens;
    latencies.push(result.latencyMs / 1000);

    const parsed = extractJson(result.content);
    const cmp = compareCase(c.expected, parsed);

    if (cmp.validJson) validJsonCount++;
    if (cmp.fullMatch) fullMatchCount++;
    for (const [k, ok] of Object.entries(cmp.fields)) {
      fieldHits[k] = (fieldHits[k] ?? 0) + (ok ? 1 : 0);
    }
  }

  const n = cases.length;
  const summaryEntry = {
    model,
    poskytovatel: provider,
    prompt: promptName,
    sada,
    pripadu: n,
    validni_json: round(validJsonCount / n),
    uplna_shoda: round(fullMatchCount / n),
    pole: Object.fromEntries(Object.entries(fieldHits).map(([k, v]) => [k, round(v / n)])),
    latence_s: round(latencies.reduce((a, b) => a + b, 0) / n),
    tokeny_vstup: totalPromptTokens,
    tokeny_vystup: totalCompletionTokens,
  };

  fs.mkdirSync('results', { recursive: true });
  const safeModel = model.replace(/[/\\]/g, '_');
  fs.writeFileSync(
    `results/raw_${sada}_${safeModel}_${promptName}.jsonl`,
    rawResponses.map(r => JSON.stringify(r)).join('\n') + '\n'
  );

  const summaryPath = 'results/summary.json';
  let summary = { student: 'Tomáš Prokeš', uloha: 'Inzeráty aut', behy: [] };
  if (fs.existsSync(summaryPath) && fs.statSync(summaryPath).size > 0) {
    summary = JSON.parse(fs.readFileSync(summaryPath, 'utf-8'));
  }

  const idx = summary.behy.findIndex(
    b => b.model === model && b.poskytovatel === provider && b.prompt === promptName && b.sada === sada
  );
  if (idx >= 0) summary.behy[idx] = summaryEntry;
  else summary.behy.push(summaryEntry);

  fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2) + '\n');

  console.log('\nVýsledek běhu:');
  console.log(summaryEntry);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
