# Kontext projektu

Projekt klasifikuje krátké české SMS zprávy. Výstup je JSON se dvěma poli:
`phishing` (`true` nebo `false`) a `typ_podvodu` (`banka`, `doruceni`,
`urady`, `investice`, `vyhra`, `ucet`, `jine` nebo `null`).

## Spuštění

Z této složky spusť:

```bash
python src/eval.py --provider openrouter --model cohere/north-mini-code:free --set dev --prompt v1
```

API klíče patří pouze do `.env`. Nikdy je nevkládej do zdrojového kódu ani do
Git repozitáře. Výsledky se ukládají do `results/` a odpovědi modelů do `cache/`.
