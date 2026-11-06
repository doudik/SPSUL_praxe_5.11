const dotenv = require('dotenv');
const OpenAI = require('openai');

dotenv.config({ quiet: true });

async function main() {
  const args = process.argv.slice(2);
  let requestedModel;
  if (args.length) {
    if (args.length !== 2 || args[0] !== '--model' || !args[1] || args[1].startsWith('--')) {
      console.error('Použití: node src/smoke-gemini.js [--model ID_MODELU]');
      process.exitCode = 1;
      return;
    }
    requestedModel = args[1];
  }

  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) {
    console.error('Chybí GEMINI_API_KEY v proměnných prostředí nebo souboru .env.');
    process.exitCode = 1;
    return;
  }

  const client = new OpenAI({
    apiKey,
    baseURL: 'https://generativelanguage.googleapis.com/v1beta/openai/',
    maxRetries: 0,
  });

  try {
    let model = requestedModel;
    if (!model) {
      const models = await client.models.list();
      const candidates = [];
      for await (const item of models) {
        candidates.push(item.id);
      }
      candidates.sort((a, b) => b.localeCompare(a, 'en', { numeric: true }));
      model = candidates.find(id => /^(?:models\/)?gemini-3\.5-flash(?:-(?:preview|latest|\d)[a-z0-9.-]*)?$/.test(id))
        ?? candidates.find(id => /^(?:models\/)?gemini-\d+(?:\.\d+)*-flash-lite(?:-(?:preview|latest|\d)[a-z0-9.-]*)?$/.test(id));
    }
    if (!model) {
      console.error('V seznamu dostupných modelů nebyl nalezen Gemini 3.5 Flash ani textový Flash-Lite.');
      process.exitCode = 1;
      return;
    }

    console.log('Model:', model);
    const response = await client.chat.completions.create({
      model,
      messages: [{ role: 'user', content: 'Odpověz pouze slovem Ahoj.' }],
      temperature: 0,
    });

    console.log('Odpověď:', response.choices[0]?.message?.content ?? '(prázdná odpověď)');
    console.log('prompt_tokens:', response.usage?.prompt_tokens ?? 'nedostupné');
    console.log('completion_tokens:', response.usage?.completion_tokens ?? 'nedostupné');
  } catch (error) {
    const status = Number.isInteger(error.status) ? error.status : 'nedostupný';
    const apiMessage = typeof error.error?.message === 'string' ? error.error.message : '';
    const safeMessage = apiMessage
      .split(apiKey).join('[SKRYTO]')
      .replace(/https?:\/\/\S+/gi, '[URL SKRYTA]')
      .replace(/\bBearer\s+\S+/gi, 'Bearer [SKRYTO]')
      .replace(/\bAIza[\w-]+/g, '[SKRYTO]');
    console.error(`Volání Gemini selhalo. HTTP status: ${status}`);
    console.error(`Zpráva API: ${safeMessage || 'nedostupná'}`);
    process.exitCode = 1;
  }
}

main();
