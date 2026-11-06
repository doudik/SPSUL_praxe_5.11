# Projekt: Evaluace extrakce hlášení závad v učebně

## Co projekt dělá
Projekt extrahuje z textových hlášení školních závad strukturovaná data do formátu JSON:
- `kategorie`: hardware | software | sit | elektrina | jine
- `priorita`: nizka | stredni | vysoka
- `ucebna`: string nebo null

Následně měří a porovnává přesnost, latenci a spotřebu tokenů různých LLM modelů na vývojové (`data/dev.jsonl`) a testovací (`data/test.jsonl`) sadě.

## Jazyk a technologie
- Python 3.10+ (používá pouze standardní knihovnu Pythonu – nulové externí závislosti)
- Podporuje API poskytovatele: Groq, NVIDIA NIM, Google Gemini, OpenRouter, Mistral

## Spuštění
Spuštění evaluace z kořenové složky repozitáře nebo složky studenta:
```bash
python studenti/maly-vilem/src/eval.py --model openai/gpt-oss-20b --provider groq --prompt v1 --dataset dev
```
nebo přímo ve složce studenta:
```bash
python src/eval.py --model openai/gpt-oss-20b --provider groq --prompt v1 --dataset dev
```
Výsledky se ukládají do `results/` a souhrn pro dashboard do `results/summary.json`.
