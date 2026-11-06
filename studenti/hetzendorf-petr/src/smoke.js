const dotenv = require('dotenv');
const OpenAI = require('openai');

dotenv.config({ quiet: true });

async function main() {
  const apiKey = process.env.GROQ_API_KEY;
  if (!apiKey) {
    console.error('Chybí GROQ_API_KEY v proměnných prostředí nebo souboru .env.');
    process.exitCode = 1;
    return;
  }

  const client = new OpenAI({
    apiKey,
    baseURL: 'https://api.groq.com/openai/v1',
  });

  try {
    const response = await client.chat.completions.create({
      model: 'openai/gpt-oss-20b',
      messages: [{ role: 'user', content: 'Odpověz pouze slovem Ahoj.' }],
      temperature: 0,
    });

    console.log('Odpověď:', response.choices[0]?.message?.content ?? '(prázdná odpověď)');
    console.log('prompt_tokens:', response.usage?.prompt_tokens ?? 'nedostupné');
    console.log('completion_tokens:', response.usage?.completion_tokens ?? 'nedostupné');
  } catch (error) {
    if (error.status === 401) {
      console.error('Ověření u Groq selhalo. Zkontrolujte platnost GROQ_API_KEY.');
    } else if (error.status === 429) {
      console.error('Groq odmítl požadavek kvůli limitu. Zkuste to později.');
    } else {
      console.error('Volání Groq selhalo. Zkontrolujte připojení a dostupnost služby.');
    }
    process.exitCode = 1;
  }
}

main();
