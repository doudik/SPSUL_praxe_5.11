# AGENTS.md - Kontext pro AI asistenty

## O projektu
- **Student**: Lukáš Černík (`studenti/cernik-lukas/`)
- **Téma úlohy**: Extrakce strukturovaných dat z bug reportů do JSON formátu.
- **Jazyk & technologie**: Python 3, `openai` klient (kompatibilní s OpenAI API pro Groq, Google Gemini, OpenRouter), `python-dotenv`.
- **Poskytovatelé modelů**: Groq (hlavní pro eval), Google Gemini (AI Studio), OpenRouter. (Mistral nepoužíváme).

## Struktura složky
- `data/dev.jsonl`: 15 vývojových případů pro ladění promptů
- `data/test.jsonl`: 10 testovacích případů pro finální eval
- `prompts/v1.txt`: Základní prompt (systémové zadání + schéma)
- `prompts/v2.txt`: Vylepšený prompt (few-shot příklady, detailnější instrukce)
- `src/eval.py`: Evaluační skript s mezipamětí v `cache/` a výpočtem metrik
- `results/summary.json`: Souhrn všech běhů pro třídní dashboard

## Jak spouštět kód
- Aktivace prostředí: `.venv\Scripts\activate` (Windows)
- Spuštění evalu: `python src/eval.py --model <model> --dataset <dev|test> --prompt <v1|v2>`
- Testovací dotaz / ověření funkčnosti: `python src/eval.py --dry-run`

