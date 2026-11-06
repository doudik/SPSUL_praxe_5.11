# AGENTS.md

## Co projekt dělá

Extrahuje strukturovaná data (značka, model, rok, nájezd v km, cena) z českých inzerátů na prodej aut a měří, jak dobře to zvládají různé LLM. Viz `README.md`.

## Jazyk a struktura

- Node.js (JavaScript, ESM - `"type": "module"` v `package.json`).
- `src/run-eval.js` - hlavní eval skript (CLI).
- `src/providers.js` - base URL a env klíč pro každého poskytovatele (Groq, Mistral, Gemini, OpenRouter).
- `src/compare.js` - porovnání odpovědi modelu s gold daty podle pravidel z README.
- `src/cache.js` - cachování odpovědí modelů podle hashe (model+prompt+vstup) do `cache/`.
- `data/dev.jsonl`, `data/test.jsonl` - testovací sada (JSONL, jeden JSON objekt na řádek).
- `prompts/v1.txt`, `prompts/v2.txt` - systémové prompty.
- `results/summary.json` - souhrn metrik ze všech běhů (formát pro dashboard třídy, neměnit klíče).
- `results/raw_*.jsonl` - surové odpovědi modelů k jednotlivým běhům.

## Příkazy

```bash
npm install
node src/run-eval.js --model=<id_modelu> --provider=<groq|mistral|gemini|openrouter> --sada=<dev|test> --prompt=<v1|v2>
```

## Testování

Žádné jednotkové testy. "Test" = spuštění `run-eval.js` na `data/test.jsonl` a kontrola `results/summary.json`.

## Konvence

- API klíče jen v `.env` (nikdy v kódu ani v gitu, viz `.env.example`).
- Čísla (`rok`, `najezd_km`, `cena`) v datech i ve výstupu modelu jako JSON number, ne string.
- Nový běh se stejnou kombinací `model+poskytovatel+prompt+sada` přepíše starý záznam v `results/summary.json`, nepřidává duplicitu.
