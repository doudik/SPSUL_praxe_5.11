# AGENTS.md – kontext pro AI asistenta

**Projekt:** eval extrakce údajů ze zpráv o počasí (úloha 17). Z krátkého českého textu se vytáhne JSON
`{"mesto", "teplota", "srazky", "typ_srazek"}` a měří se, jak přesně to zvládají různé LLM.

- Jazyk: Python 3.9+, **jen standardní knihovna** (žádné `pip install`).
- Data: `data/dev.jsonl` (15 případů, na ladění), `data/test.jsonl` (10 případů, NIKDY neladit).
- Prompty: `prompts/v1.txt`, `prompts/v2.txt` (zástupný text `{text}`).
- Hlavní skript: `src/eval.py` – volá OpenAI-kompatibilní API, cache v `cache/`, výsledky v `results/`.
- `src/run_all.py` ověří klíče, pustí všechny experimenty (při nefunkčním modelu vezme zálohu), `src/report.py` vyrobí tabulku do README, rozbor chyb a dashboard.
- Spuštění: `python src/eval.py --sada dev --prompt v1 --poskytovatel groq --model openai/gpt-oss-20b`
- Klíče jsou v `.env` (není v gitu!). Názvy proměnných viz `.env.example`.
- Pracuje se jen ve složce `studenti/koritko-jan/`. Formát `results/summary.json` neměnit.
