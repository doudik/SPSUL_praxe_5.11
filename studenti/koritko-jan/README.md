# Koritko Jan – úloha 17: Zprávy o počasí

## Co nástroj dělá

Nástroj dostane krátký český text o počasí (předpověď, SMS od kamaráda, hlášení z hor…) a pomocí LLM z něj
vytáhne strukturované údaje do JSONu: **o jakém místě zpráva je, jaká je teplota a jestli jsou srážky a jaké**.
K nástroji patří testovací sada 25 ručně ověřených případů a evaluační skript, který změří, jak přesně to
zvládají různé modely a prompty.

## Schéma výstupu

```json
{
  "mesto": "string nebo null",
  "teplota": "celé číslo (°C) nebo null",
  "srazky": "true | false | null",
  "typ_srazek": "dest | snih | dest_se_snehem | bourka | krupobiti | zadne | null"
}
```

| Pole | Typ | Význam |
|---|---|---|
| `mesto` | string / null | místo, pro které zpráva popisuje počasí, v 1. pádě („v Ostravě“ → „Ostrava“). Více míst → první místo, pro které je počasí popsané. Text, který není zprávou o počasí → `null`. |
| `teplota` | int / null | teplota ve °C. Rozpětí nebo ráno/odpoledne → **nejvyšší** denní hodnota. Slovy („patnáct“, „minus osm“, „kolem nuly“) → číslo. °F → přepočet na °C a zaokrouhlení. Neuvedeno → `null`. |
| `srazky` | bool / null | `true` = zpráva uvádí nebo předpovídá srážky (i „možná sprchne“). `false` = výslovně bez srážek / sucho / jasno / slunečno. `null` = o srážkách nic (mlha a oblačnost nejsou srážky). |
| `typ_srazek` | enum / null | `dest` (déšť, přeháňky, mrholení), `snih`, `dest_se_snehem` (i déšť přecházející ve sněžení), `bourka`, `krupobiti`; `zadne` když `srazky = false`; `null` když `srazky = null`. |

## Pravidla porovnávání

- **mesto**: nezáleží na velikosti písmen, diakritice ani na mezerách a pomlčkách navíc („plzen“ = „Plzeň“,
  „Ústí nad  Labem“ = „usti nad labem“). Jiný pád („v Praze“) je chyba.
- **teplota**: porovnává se číslo po zaokrouhlení na celé stupně. Když model vrátí text („14 °C“, „-3“), vezme
  se z něj číslo. `null` musí odpovídat `null`.
- **srazky**: musí sedět `true` / `false` / `null`. Toleruje se zápis jako text („true“, „ano“, „ne“).
- **typ_srazek**: přesná shoda s povolenou hodnotou (bez ohledu na velikost písmen a diakritiku).
- **Úplná shoda** = sedí všechna 4 pole. Nevalidní JSON = všechna pole špatně.

## Testovací sada

- `data/dev.jsonl` – 15 případů (id 1–15), na nich se ladí prompt. 7 záludných.
- `data/test.jsonl` – 10 případů (id 16–25), použité **jen** na finální měření. 5 záludných.
- Záludné případy (`"tezky": true`): číslovky slovy (#6, #12, #22, #23), chybějící teplota (#7), chybějící
  informace o srážkách (#13, #25), text bez diakritiky / s překlepy (#8, #22), ironie (#11), dvě města
  v jednom textu (#14, #25), teplota ve °F (#19), text, který vůbec není zprávou o počasí (#20).
- Few-shot příklady v `prompts/v2.txt` (Kolín, Tábor, Přerov) jsou vymyšlené zvlášť a nejsou z dev ani test sady.

## Jak spustit

Potřebuješ jen **Python 3.9+** – skript používá jen standardní knihovnu, nic se neinstaluje.

```bash
cd studenti/koritko-jan
cp .env.example .env          # a do .env vlož své klíče (GROQ_API_KEY, MISTRAL_API_KEY, ...)

# jeden běh
python src/eval.py --sada dev --prompt v1 --poskytovatel groq --model openai/gpt-oss-20b

# všechny experimenty z Fáze 4 (3 modely × v1/v2 na dev, pak 2 nejlepší na test) + report
python src/run_all.py

# jen přegenerovat tabulku, rozbor chyb, cenu a dashboard (bez volání API)
python src/report.py
```

Parametry `eval.py`: `--sada dev|test`, `--prompt v1|v2`, `--poskytovatel groq|mistral|gemini|openrouter|nvidia`,
`--model <název>`, volitelně `--json-mode` (pošle `response_format: json_object`).

Co skript dělá: pošle každý případ modelu s `temperature: 0`, odpověď zkusí rozparsovat jako JSON (nevalidní
výstup se započítá, program nespadne), porovná pole podle pravidel výše, měří latenci a tokeny, při chybě 429
počká a zkusí znovu. Odpovědi ukládá do `cache/` (klíč = SHA-256 z poskytovatele, modelu a celého promptu se
vstupem), takže druhé spuštění nevolá API. Surové odpovědi jsou v `results/<sada>_<prompt>_<poskytovatel>_<model>.json`,
souhrn všech běhů v `results/summary.json` (stejný běh se přepíše).

## Výsledky

Tabulku generuje `src/report.py` přímo z `results/summary.json`, čísla tedy vždy odpovídají souborům.

<!-- TABULKA START -->
_Zatím nespuštěno – po `python src/run_all.py` se sem vloží tabulka._
<!-- TABULKA KONEC -->

Použité modely: `openai/gpt-oss-20b` (Groq, ~20 mld. parametrů), `llama-3.3-70b-versatile` (Groq, 70 mld.),
`mistral-small-latest` (Mistral, ~24 mld.). Grafy: [`results/dashboard.html`](results/dashboard.html).
Seznam všech chyb: [`results/chyby.md`](results/chyby.md).

## Rozbor 3 chyb

_DOPLNIT po spuštění evalu – podklady jsou v `results/chyby.md`._

1. …
2. …
3. …

## Doporučení pro 10 000 dotazů denně

Odhad ceny (ceny placených variant na OpenRouteru ověřené 6. 11. 2026, kurz 23 Kč/USD), počítáno z naměřených tokenů:

<!-- CENA START -->
_Zatím nespuštěno._
<!-- CENA KONEC -->

_DOPLNIT: který model + prompt a proč (přesnost, rychlost, cena)._

## Rozdíl dev a test

_DOPLNIT po finálním měření._

## AI asistent

- Kód, testovací sada, prompty i tento README vznikly s pomocí **Claude (Anthropic)** v aplikaci Claude.
  Správné odpovědi (gold) jsem zkontroloval sám případ po případu.
- OpenCode: _DOPLNIT – jaký model (Devstral / …), s čím pomohl, kde selhal._

## Reflexe

_DOPLNIT 5–10 vět vlastními slovy._
