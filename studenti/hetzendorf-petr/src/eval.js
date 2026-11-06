const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { performance } = require('node:perf_hooks');
const dotenv = require('dotenv');
const OpenAI = require('openai');

const root = path.join(__dirname, '..');
const providers = {
  groq: { key: 'GROQ_API_KEY', baseURL: 'https://api.groq.com/openai/v1' },
  gemini: { key: 'GEMINI_API_KEY', baseURL: 'https://generativelanguage.googleapis.com/v1beta/openai/' },
  openrouter: { key: 'OPENROUTER_API_KEY', baseURL: 'https://openrouter.ai/api/v1' },
};
const pizzaNames = new Set(['margherita', 'salamova', 'hawai', 'quattro formaggi']);
const maxRetries = 3;

function parseArgs(args) {
  const options = {};
  for (let i = 0; i < args.length;) {
    const flag = args[i];
    if (flag === '--cache-only' && !Object.hasOwn(options, flag)) {
      options[flag] = true;
      i++;
      continue;
    }
    const value = args[i + 1];
    if (!['--provider', '--model', '--split', '--prompt'].includes(flag) ||
        !value || value.startsWith('--') || Object.hasOwn(options, flag)) {
      throw new Error('Použití: node src/eval.js --provider groq|gemini|openrouter --model ID --split dev|test --prompt NAZEV');
    }
    options[flag] = value;
    i += 2;
  }
  if (!Object.hasOwn(providers, options['--provider']) || !options['--model'] ||
      !['dev', 'test'].includes(options['--split']) || !/^[a-zA-Z0-9_-]+$/.test(options['--prompt'] || '')) {
    throw new Error('Zadejte platné parametry --provider, --model, --split a --prompt.');
  }
  return {
    provider: options['--provider'], model: options['--model'],
    split: options['--split'], prompt: options['--prompt'],
    cacheOnly: options['--cache-only'] === true,
  };
}

function saveCachedResults(resultsDir, records, options) {
  const comparable = ['id', 'model', 'provider', 'raw_response', 'latency_ms', 'prompt_tokens', 'completion_tokens'];
  let updated = 0;
  for (const name of fs.readdirSync(resultsDir)) {
    if (!name.startsWith('run-') || !name.endsWith('.jsonl')) continue;
    const file = path.join(resultsDir, name);
    let previous;
    try {
      previous = fs.readFileSync(file, 'utf8').split(/\r?\n/).filter((line) => line.trim()).map(JSON.parse);
    } catch { continue; }
    if (previous.length !== records.length || !previous.every((row, i) =>
      comparable.every((key) => row[key] === records[i][key]))) continue;
    const revised = previous.map((row, i) => ({ ...row, valid_json: records[i].valid_json, shoda: records[i].shoda }));
    fs.writeFileSync(file, `${revised.map((row) => JSON.stringify(row)).join('\n')}\n`, 'utf8');
    updated++;
  }
  if (!updated) {
    const id = crypto.createHash('sha256').update(JSON.stringify({ provider: options.provider, model: options.model,
      prompt: options.prompt, split: options.split })).digest('hex');
    const file = path.join(resultsDir, `run-cache-${id}.jsonl`);
    fs.writeFileSync(file, `${records.map((row) => JSON.stringify(row)).join('\n')}\n`, 'utf8');
    updated = 1;
  }
  return updated;
}

function validItems(items) {
  return Array.isArray(items) && items.every((item) =>
    item !== null && typeof item === 'object' && !Array.isArray(item) &&
    Object.hasOwn(item, 'nazev') && pizzaNames.has(item.nazev) &&
    Object.hasOwn(item, 'pocet') &&
    (item.pocet === null || (Number.isSafeInteger(item.pocet) && item.pocet > 0)));
}

function validAddress(value) {
  return value === null || typeof value === 'string';
}

function validPayment(value) {
  return value === null || value === 'karta' || value === 'hotovost';
}

function validExpected(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value) &&
    Object.hasOwn(value, 'polozky') && validItems(value.polozky) &&
    Object.hasOwn(value, 'adresa') && validAddress(value.adresa) &&
    Object.hasOwn(value, 'platba') && validPayment(value.platba);
}

function compare(raw, expected) {
  let actual;
  try {
    actual = JSON.parse(raw);
  } catch {
    return { validJson: false, polozky: false, adresa: false, platba: false, full: false };
  }
  const object = actual !== null && typeof actual === 'object' && !Array.isArray(actual);
  const itemsValid = object && Object.hasOwn(actual, 'polozky') && validItems(actual.polozky);
  const addressValid = object && Object.hasOwn(actual, 'adresa') && validAddress(actual.adresa);
  const paymentValid = object && Object.hasOwn(actual, 'platba') && validPayment(actual.platba);
  const sortedItems = (items) => items.map((item) => JSON.stringify([item.nazev, item.pocet])).sort();
  const normalizeAddress = (address) => address === null ? null : address.trim().replace(/\s+/gu, ' ').toLocaleLowerCase('cs-CZ');
  const polozky = Boolean(itemsValid && JSON.stringify(sortedItems(actual.polozky)) === JSON.stringify(sortedItems(expected.polozky)));
  const adresa = Boolean(addressValid && normalizeAddress(actual.adresa) === normalizeAddress(expected.adresa));
  const platba = Boolean(paymentValid && actual.platba === expected.platba);
  return { validJson: true, polozky, adresa, platba, full: polozky && adresa && platba };
}

function retryDelay(error, attempt) {
  const header = error.headers?.get?.('retry-after');
  if (header) {
    const seconds = Number(header);
    if (Number.isFinite(seconds) && seconds >= 0) return seconds * 1000;
    const date = Date.parse(header);
    if (Number.isFinite(date)) return Math.max(0, date - Date.now());
  }
  return 1000 * 2 ** attempt;
}

async function sleep(ms) {
  // setTimeout má omezený rozsah; delší Retry-After proto rozdělíme.
  const until = Date.now() + ms;
  while (Date.now() < until) {
    await new Promise((resolve) => setTimeout(resolve, Math.min(until - Date.now(), 2147483647)));
  }
}

async function checkOpenRouterQuota() {
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) throw new Error('Chybí OPENROUTER_API_KEY v prostředí nebo .env.');
  let response;
  try {
    response = await fetch('https://openrouter.ai/api/v1/key', {
      headers: { Authorization: `Bearer ${apiKey}` },
      signal: AbortSignal.timeout(30000),
    });
  } catch {
    throw new Error('Kvótu OpenRouteru se nepodařilo zjistit.');
  }
  if (!response.ok) throw new Error(`Kvótu OpenRouteru se nepodařilo zjistit (HTTP ${response.status}).`);
  let data;
  try { data = await response.json(); } catch { throw new Error('Kvóta OpenRouteru není dostupná.'); }
  const remaining = data?.data?.free_model_daily_requests?.remaining;
  if (!Number.isSafeInteger(remaining) || remaining < 0) throw new Error('Kvóta OpenRouteru není dostupná.');
  console.log(`Zbývající denní free kvóta: ${remaining}`);
  if (remaining < 15) throw new Error('Pro měření je potřeba alespoň 15 zbývajících free požadavků.');
}

function readCases(split) {
  const content = fs.readFileSync(path.join(root, 'data', `${split}.jsonl`), 'utf8');
  const lines = content.split(/\r?\n/).filter((line) => line.trim());
  if (!lines.length) throw new Error('Datová sada je prázdná.');
  const ids = new Set();
  return lines.map((line, index) => {
    let item;
    try { item = JSON.parse(line); } catch { throw new Error(`Neplatný JSON na řádku ${index + 1} datové sady.`); }
    if (!item || !Number.isSafeInteger(item.id) || typeof item.input !== 'string' || !validExpected(item.expected)) {
      throw new Error(`Neplatný případ nebo expected na řádku ${index + 1} datové sady.`);
    }
    if (ids.has(item.id)) throw new Error(`Duplicitní ID ${item.id} v datové sadě.`);
    ids.add(item.id);
    return item;
  });
}

function isMeasurement(value) {
  return value && typeof value.raw === 'string' && Number.isFinite(value.latencyMs) && value.latencyMs >= 0 &&
    Number.isSafeInteger(value.promptTokens) && value.promptTokens >= 0 &&
    Number.isSafeInteger(value.completionTokens) && value.completionTokens >= 0;
}

function saveSummary(run) {
  const file = path.join(root, 'results', 'summary.json');
  let summary = { student: 'Petr Hetzendorf', uloha: 'Objednávky v pizzerii', behy: [] };
  if (fs.existsSync(file)) {
    const previous = JSON.parse(fs.readFileSync(file, 'utf8'));
    if (!previous || !Array.isArray(previous.behy)) throw new Error('Neplatný existující souhrn.');
    summary.behy = previous.behy;
  }
  summary.behy = summary.behy.filter((entry) => !(entry.model === run.model &&
    entry.poskytovatel === run.poskytovatel && entry.prompt === run.prompt && entry.sada === run.sada));
  summary.behy.push(run);
  const temp = `${file}.${crypto.randomUUID()}.tmp`;
  try {
    fs.writeFileSync(temp, `${JSON.stringify(summary, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' });
    fs.renameSync(temp, file);
  } finally {
    if (fs.existsSync(temp)) fs.unlinkSync(temp);
  }
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (!options.cacheOnly) {
    dotenv.config({ quiet: true, path: path.join(root, '.env') });
    if (options.provider === 'openrouter') await checkOpenRouterQuota();
  }
  const prompt = fs.readFileSync(path.join(root, 'prompts', `${options.prompt}.txt`), 'utf8');
  const cases = readCases(options.split);
  const cacheDir = path.join(root, 'cache');
  const resultsDir = path.join(root, 'results');
  fs.mkdirSync(cacheDir, { recursive: true });
  fs.mkdirSync(resultsDir, { recursive: true });
  const resultFile = path.join(resultsDir, `run-${new Date().toISOString().replace(/[:.]/g, '-')}-${crypto.randomUUID()}.jsonl`);
  const stats = { api: 0, cache: 0, validJson: 0, polozky: 0, adresa: 0, platba: 0, full: 0, latencyMs: 0, promptTokens: 0, completionTokens: 0 };
  let client;
  let openrouterRequestMade = false;
  const records = [];

  try {
    for (const item of cases) {
      const request = { model: options.model, temperature: 0, messages: [
        { role: 'system', content: prompt }, { role: 'user', content: item.input },
      ] };
      const hash = crypto.createHash('sha256').update(JSON.stringify({ provider: options.provider, request })).digest('hex');
      const cacheFile = path.join(cacheDir, `${hash}.json`);
      let measurement;
      let cached = false;
      if (fs.existsSync(cacheFile)) {
        try { measurement = JSON.parse(fs.readFileSync(cacheFile, 'utf8')); } catch { measurement = null; }
        if (isMeasurement(measurement)) { cached = true; stats.cache++; }
        else measurement = null;
      }
      if (!measurement) {
        if (options.cacheOnly) throw new Error(`Pro ID ${item.id} chybí platný záznam v cache.`);
        if (!client) {
          const config = providers[options.provider];
          const apiKey = process.env[config.key];
          if (!apiKey) throw new Error(`Chybí ${config.key} v prostředí nebo .env.`);
          client = new OpenAI({ apiKey, baseURL: config.baseURL, maxRetries: 0 });
        }
        let response;
        let latencyMs;
        for (let attempt = 0; attempt <= maxRetries; attempt++) {
          if (options.provider === 'openrouter') {
            if (openrouterRequestMade) await sleep(3200);
            openrouterRequestMade = true;
          }
          stats.api++;
          const started = performance.now();
          try {
            response = await client.chat.completions.create(request);
            latencyMs = performance.now() - started;
            break;
          } catch (error) {
            if (error.status !== 429 || attempt === maxRetries) {
              const status = Number.isInteger(error.status) ? `HTTP ${error.status}` : 'bez HTTP statusu';
              throw new Error(`API selhalo pro ID ${item.id} (${status}).`);
            }
            const wait = retryDelay(error, attempt);
            console.log(`HTTP 429 pro ID ${item.id}; opakování ${attempt + 1}/${maxRetries} po ${Math.ceil(wait / 1000)} s.`);
            await sleep(wait);
          }
        }
        measurement = {
          raw: response.choices?.[0]?.message?.content ?? '', latencyMs,
          promptTokens: response.usage?.prompt_tokens, completionTokens: response.usage?.completion_tokens,
        };
        if (!isMeasurement(measurement)) throw new Error(`API pro ID ${item.id} nevrátilo úplné údaje o odpovědi a tokenech.`);
        fs.writeFileSync(cacheFile, `${JSON.stringify(measurement)}\n`, 'utf8');
      }

      const match = compare(measurement.raw, item.expected);
      const record = { id: item.id, model: options.model, provider: options.provider,
        raw_response: measurement.raw, latency_ms: measurement.latencyMs, prompt_tokens: measurement.promptTokens,
        completion_tokens: measurement.completionTokens, cache: cached, valid_json: match.validJson,
        shoda: { polozky: match.polozky, adresa: match.adresa, platba: match.platba, uplna: match.full } };
      if (options.cacheOnly) records.push(record);
      else fs.appendFileSync(resultFile, `${JSON.stringify(record)}\n`, 'utf8');
      for (const key of ['validJson', 'polozky', 'adresa', 'platba', 'full']) stats[key] += Number(match[key]);
      stats.latencyMs += measurement.latencyMs;
      stats.promptTokens += measurement.promptTokens;
      stats.completionTokens += measurement.completionTokens;
    }

    const count = cases.length;
    const run = {
      model: options.model, poskytovatel: options.provider, prompt: options.prompt, sada: options.split,
      pripadu: count, validni_json: stats.validJson / count, uplna_shoda: stats.full / count,
      pole: { polozky: stats.polozky / count, adresa: stats.adresa / count, platba: stats.platba / count },
      latence_s: stats.latencyMs / count / 1000, tokeny_vstup: stats.promptTokens, tokeny_vystup: stats.completionTokens,
    };
    const updated = options.cacheOnly ? saveCachedResults(resultsDir, records, options) : 0;
    saveSummary(run);
    console.log(JSON.stringify(run, null, 2));
    if (options.cacheOnly) console.log(`Aktualizované soubory výsledků: ${updated}`);
    else console.log(`Výsledky: ${resultFile}`);
  } finally {
    console.log(`API volání: ${stats.api}; zásahy do cache: ${stats.cache}`);
  }
}

main().catch((error) => {
  // Nevypisujeme objekty chyb poskytovatelů ani jejich hlavičky.
  console.error(`Evaluace nebyla dokončena: ${error.message}`);
  process.exitCode = 1;
});
