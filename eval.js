import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import dotenv from 'dotenv';
import Groq from 'groq-sdk';
import { GoogleGenAI } from '@google/genai';

dotenv.config();

// ==========================================
// KONFIGURACE (Možno měnit před spuštěním)
// ==========================================
const STUDENT_NAME = "Lukáš Svoboda";
const ULOHA_NAME = "Komentáře na fóru";

// Získej z argumentů příkazové řádky nebo použij výchozí
// Příkaz pro spuštění: node eval.js --provider=groq --model=llama-3.3-70b-versatile --prompt=v1 --sada=dev
const args = parseArgs(process.argv.slice(2));

const PROVIDER = args.provider || process.env.PROVIDER || "groq";
const MODEL = args.model || process.env.MODEL || "llama-3.3-70b-versatile";
const PROMPT_NAME = args.prompt || "v1";
const SADA_NAME = args.sada || "dev";

// Zajištění existence potřebných složek
if (!fs.existsSync('cache')) fs.mkdirSync('cache', { recursive: true });
if (!fs.existsSync('results')) fs.mkdirSync('results', { recursive: true });

// Pomocná funkce pro sleep
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Pomocná funkce pro parsování CLI argumentů
function parseArgs(cliArgs) {
  const result = {};
  for (const arg of cliArgs) {
    if (arg.startsWith('--')) {
      const [key, value] = arg.slice(2).split('=');
      result[key] = value;
    }
  }
  return result;
}

// Načtení datové sady (.jsonl nebo .json)
// Načtení datové sady (podporuje .json i .jsonl automaticky)
function loadDataset(sadaName) {
  const jsonlPath = path.join('data', `${sadaName}.jsonl`);
  const jsonPath = path.join('data', `${sadaName}.json`);

  let filePath = fs.existsSync(jsonlPath) ? jsonlPath : fs.existsSync(jsonPath) ? jsonPath : null;

  if (!filePath) {
    throw new Error(`Datový soubor pro sadu '${sadaName}' nebyl nalezen v data/${sadaName}.jsonl ani data/${sadaName}.json!`);
  }

  const content = fs.readFileSync(filePath, 'utf8').trim();

  // Pokud soubor začíná '[', jde o klasický JSON pole
  if (content.startsWith('[')) {
    return JSON.parse(content);
  }

  // Jinak zpracujeme jako JSONL (jeden JSON objekt na řádek)
  return content
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line));
}

// Klient pro vybraný poskytovatel API
async function callLLM(prov, model, systemPrompt, userMessage) {
  if (prov === 'groq') {
    const apiKey = process.env.GROQ_API_KEY;
    if (!apiKey) throw new Error("V .env chybí GROQ_API_KEY!");
    const client = new Groq({ apiKey });
    const completion = await client.chat.completions.create({
      model: model,
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userMessage }
      ],
      temperature: 0
    });
    return {
      content: completion.choices[0]?.message?.content || "",
      promptTokens: completion.usage?.prompt_tokens || 0,
      completionTokens: completion.usage?.completion_tokens || 0
    };
  } 
  else if (prov === 'mistral' || prov === 'openrouter') {
    const baseUrl = prov === 'mistral' 
      ? 'https://api.mistral.ai/v1/chat/completions' 
      : 'https://openrouter.ai/api/v1/chat/completions';
    const apiKey = prov === 'mistral' ? process.env.MISTRAL_API_KEY : process.env.OPENROUTER_API_KEY;
    if (!apiKey) throw new Error(`V .env chybí klíč pro ${prov}!`);

    const res = await fetch(baseUrl, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey.trim()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: model,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userMessage }
        ],
        temperature: 0
      })
    });
    if (!res.ok) throw new Error(`API Error ${res.status}: ${await res.text()}`);
    const data = await res.json();
    return {
      content: data.choices[0]?.message?.content || "",
      promptTokens: data.usage?.prompt_tokens || 0,
      completionTokens: data.usage?.completion_tokens || 0
    };
  } 
  else if (prov === 'gemini' || prov === 'google') {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) throw new Error("V .env chybí GEMINI_API_KEY!");

    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        contents: [
          {
            role: 'user',
            parts: [{ text: `${systemPrompt}\n\nVstup k analýze:\n${userMessage}` }]
          }
        ],
        generationConfig: {
          temperature: 0,
          responseMimeType: "application/json"
        }
      })
    });

    if (!res.ok) throw new Error(`Gemini API Error ${res.status}: ${await res.text()}`);
    const data = await res.json();
    return {
      content: data.candidates?.[0]?.content?.parts?.[0]?.text || "",
      promptTokens: data.usageMetadata?.promptTokenCount || 0,
      completionTokens: data.usageMetadata?.candidatesTokenCount || 0
    };
  }

  throw new Error(`Neznámý poskytovatel: ${prov}`);
}

// Hlavní evaluační logika
async function runEval() {
  console.log(`🚀 Spouštím evaluaci: Poskytovatel=${PROVIDER}, Model=${MODEL}, Prompt=${PROMPT_NAME}, Sada=${SADA_NAME}`);

  // 1. Načtení promptu
  const promptPath = path.join('prompts', `${PROMPT_NAME}.txt`);
  if (!fs.existsSync(promptPath)) {
    throw new Error(`Soubor s promptem nebyl nalezen: ${promptPath}`);
  }
  const systemPrompt = fs.readFileSync(promptPath, 'utf8');

  // 2. Načtení datasetu
  const dataset = loadDataset(SADA_NAME);
  console.log(`📋 Načteno ${dataset.length} případů ze sady '${SADA_NAME}'`);

  let totalTokensVstup = 0;
  let totalTokensVystup = 0;
  let totalLatency = 0;
  let validJsonCount = 0;
  let fullMatchCount = 0;

  // Počítadlo shod pro pole
  const fieldMatches = { typ: 0, skore_toxicity: 0, akce: 0 };
  const rawResponses = [];

  for (let i = 0; i < dataset.length; i++) {
    const item = dataset[i];
    const cacheKeyInput = `${PROVIDER}_${MODEL}_${PROMPT_NAME}_${item.input}`;
    const hash = crypto.createHash('sha256').update(cacheKeyInput).digest('hex');
    const cacheFilePath = path.join('cache', `${hash}.json`);

    let responseData = null;
    let latencySec = 0;

    // KONTROLA MEZIPAMĚTI
    if (fs.existsSync(cacheFilePath)) {
      const cached = JSON.parse(fs.readFileSync(cacheFilePath, 'utf8'));
      responseData = cached.responseData;
      latencySec = cached.latencySec;
      console.log(`[${i + 1}/${dataset.length}] ID ${item.id} -> Načteno z cache`);
    } else {
      let success = false;
      let attempts = 0;

      while (!success && attempts < 5) {
        try {
          attempts++;
          const startTime = Date.now();

          responseData = await callLLM(PROVIDER, MODEL, systemPrompt, item.input);

          const endTime = Date.now();
          latencySec = (endTime - startTime) / 1000;
          success = true;

          // Uložení do mezipaměti
          fs.writeFileSync(cacheFilePath, JSON.stringify({ responseData, latencySec }));
          console.log(`[${i + 1}/${dataset.length}] ID ${item.id} -> Volání API OK (${latencySec.toFixed(2)}s)`);

          // Pauza 500ms proti rate limitu
          await sleep(500);
        } catch (error) {
          if (error.status === 429 || (error.message && error.message.includes('429'))) {
            console.warn(`⚠️ Chyba 429 (Rate limit) u ID ${item.id}. Čekám 15s... (Pokus ${attempts})`);
            await sleep(15000);
          } else {
            console.error(`❌ Chyba u ID ${item.id}:`, error.message);
            break;
          }
        }
      }
    }

    if (!responseData) continue;

    // Sběr metrik tokenů a času
    totalTokensVstup += responseData.promptTokens;
    totalTokensVystup += responseData.completionTokens;
    totalLatency += latencySec;

    const rawContent = responseData.content || "";
    rawResponses.push({ id: item.id, raw: rawContent });

    // PARSOVÁNÍ JSON ODPODVĚDI (odolnost vůči markdownu)
    let parsed = null;
    let cleanedText = rawContent.trim();

    if (cleanedText.startsWith('```')) {
      cleanedText = cleanedText.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '').trim();
    }

    try {
      parsed = JSON.parse(cleanedText);
      validJsonCount++;
    } catch (e) {
      parsed = null;
    }

    // POROVNÁNÍ S EXPECTED SE ZAPOČÍTÁNÍM SHOD
    // Pomocná funkce pro odstranění diakritiky a mezer
    const normalize = (str) => 
    String(str ?? '')
        .trim()
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/\s+/g, "_");

    if (parsed && item.expected) {
    let isFullMatch = true;
    const fieldsToCheck = ['typ', 'skore_toxicity', 'akce'];

    for (const field of fieldsToCheck) {
        const valActual = normalize(parsed[field]);
        const valExpected = normalize(item.expected[field]);

        if (valActual === valExpected && valExpected !== '') {
        fieldMatches[field]++;
        } else {
        isFullMatch = false;
        console.log(`⚠️ ID ${item.id} [${field}]: Model vrátil "${parsed[field]}", očekáváno "${item.expected[field]}"`);
        }
    }

    if (isFullMatch) {
        fullMatchCount++;
        console.log(`✅ ID ${item.id}: Plná shoda!`);
    }
    }
  }

  const n = dataset.length;
  const avgLatency = n > 0 ? totalLatency / n : 0;

  // Souhrnný objekt jednoho běhu
  const summaryRun = {
    model: MODEL,
    poskytovatel: PROVIDER,
    prompt: PROMPT_NAME,
    sada: SADA_NAME,
    pripadu: n,
    validni_json: n > 0 ? Number((validJsonCount / n).toFixed(2)) : 0,
    uplna_shoda: n > 0 ? Number((fullMatchCount / n).toFixed(2)) : 0,
    pole: {
      typ: n > 0 ? Number((fieldMatches.typ / n).toFixed(2)) : 0,
      skore_toxicity: n > 0 ? Number((fieldMatches.skore_toxicity / n).toFixed(2)) : 0,
      akce: n > 0 ? Number((fieldMatches.akce / n).toFixed(2)) : 0
    },
    latence_s: Number(avgLatency.toFixed(2)),
    tokeny_vstup: totalTokensVstup,
    tokeny_vystup: totalTokensVystup
  };

  // Uložení surových odpovědí
  fs.writeFileSync('results/raw_responses.json', JSON.stringify(rawResponses, null, 2));

  // ZÁPIS DO RESULTS/SUMMARY.JSON (Přepsání předchozího stejného běhu)
  const summaryFilePath = 'results/summary.json';
  let summaryData = { student: STUDENT_NAME, uloha: ULOHA_NAME, behy: [] };

  if (fs.existsSync(summaryFilePath)) {
    try {
      summaryData = JSON.parse(fs.readFileSync(summaryFilePath, 'utf8'));
    } catch (e) {
      // Ignorujeme případný chybný obsah
    }
  }

  // Přepsání běhu se stejnou kombinací (model + prompt + sada)
  summaryData.behy = (summaryData.behy || []).filter(
    (b) => !(b.model === MODEL && b.prompt === PROMPT_NAME && b.sada === SADA_NAME)
  );
  summaryData.behy.push(summaryRun);

  fs.writeFileSync(summaryFilePath, JSON.stringify(summaryData, null, 2));

  console.log("\n==========================================");
  console.log("   VÝSLEDKY BĚHU (RESULTS/SUMMARY.JSON)");
  console.log("==========================================");
  console.log(JSON.stringify(summaryRun, null, 2));
}

runEval().catch((err) => {
  console.error("FATÁLNÍ CHYBA:", err.message);
  process.exit(1);
});