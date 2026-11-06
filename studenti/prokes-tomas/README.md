# Inzeráty aut: značka, model, rok, nájezd v km, cena

## Co nástroj dělá

Nástroj vezme text inzerátu na prodej auta a vytáhne z něj strukturované údaje do JSONu: značku, model, rok výroby, nájezd v km a cenu. Hodí se například na porovnávání nabídek z různých bazarů aut v jednotném formátu.

## Schéma výstupu

```json
{
  "znacka": "string nebo null",
  "model": "string nebo null",
  "rok": "number nebo null",
  "najezd_km": "number nebo null",
  "cena": "number nebo null"
}
```

- `znacka` – výrobce auta, např. `"Škoda"`, `"Volkswagen"`, `"BMW"`.
- `model` – model auta, např. `"Octavia"`, `"Golf"`.
- `rok` – rok výroby jako celé číslo, např. `2015`. `null`, pokud text rok neuvádí.
- `najezd_km` – nájezd v kilometrech jako celé číslo, např. `150000`. `null`, pokud text nájezd neuvádí.
- `cena` – cena v Kč jako celé číslo, např. `350000`. `null`, pokud text cenu neuvádí.
- Pokud text vůbec není inzerátem na prodej auta (nebo žádný z údajů nelze z textu zjistit), mají `null` i `znacka` a `model`.

## Pravidla porovnávání

- `znacka` a `model`: nerozlišuje se velikost písmen a přebytečné mezery na začátku/konci se ignorují (`"škoda"` = `"Škoda"` = `" Škoda "`).
- Běžné zkratky výrobců se považují za shodné s plným názvem (`"VW"` = `"Volkswagen"`).
- `model`: generační označení (`VII`, `Mk7` apod.) se do pole nezahrnuje, pokud není oficiální součástí názvu modelu (`"Golf VII"` → `"Golf"`).
- `rok`: musí sedět přesně jako číslo (ne jako text, tedy `2015`, ne `"2015"`).
- `najezd_km`: porovnává se jako číslo po normalizaci zápisu – mezery, tečky jako oddělovač tisíců a jednotka `km` se ignorují (`"150 000 km"` = `"150.000 km"` = `150000`). Číslovky vypsané slovy (`"sto padesát tisíc"`) se počítají stejně.
- `cena`: porovnává se jako číslo po normalizaci zápisu – mezery, oddělovače tisíců a měna (`Kč`, `,-`) se ignorují (`"350 000 Kč"` = `"350000,-"` = `350000`). Zkratka `"220k"` se počítá jako `220000`.
- Pokud text daný údaj neobsahuje nebo je natolik nejednoznačný, že ho nejde spolehlivě určit, očekávaná hodnota je `null` a jako správná se uzná jen `null` (ne prázdný řetězec nebo `0`).

## Jak spustit

```bash
npm install
node src/run-eval.js --model=<id_modelu> --provider=<groq|mistral|gemini|openrouter> --sada=<dev|test> --prompt=<v1|v2>
```

## Výsledky

### 4a + 4b: porovnání modelů a promptů (sada `dev`, 15 případů)

| Model | Poskytovatel | Prompt | Validní JSON | Úplná shoda | znacka | model | rok | najezd_km | cena | Latence | Tokeny (vstup/výstup) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-oss-20b | Groq | v1 | 100 % | 80,0 % | 93 % | 93 % | 100 % | 93 % | 93 % | 0,74 s | 7795 / 3114 |
| gpt-oss-120b | Groq | v1 | 100 % | 93,3 % | 100 % | 93 % | 100 % | 100 % | 100 % | 0,79 s | 7795 / 2809 |
| gemini-3.5-flash-lite | Gemini | v1 | 100 % | 93,3 % | 100 % | 93 % | 100 % | 100 % | 100 % | 1,36 s | 7066 / 892 |
| gpt-oss-20b | Groq | **v2** | 93,3 % | 86,7 % | 87 % | 93 % | 93 % | 93 % | 93 % | 0,81 s | 13510 / 5328 |
| gpt-oss-120b | Groq | **v2** | 100 % | 93,3 % | 100 % | 100 % | 100 % | 93 % | 100 % | 0,86 s | 13510 / 3115 |
| gemini-3.5-flash-lite | Gemini | **v2** | 100 % | **100 %** | 100 % | 100 % | 100 % | 100 % | 100 % | 1,39 s | 13321 / 857 |

Ve `v1` selhaly všechny tři modely na stejném případu (č. 8 – model `320d` uvedený samostatně na konci věty, oddělený od značky). `prompts/v2.txt` přidal few-shot příklady a instrukci číst celou větu, což tuhle chybu u všech modelů opravilo. U `gpt-oss-20b` se zároveň objevila nová nestabilita (viz rozbor chyb níže).

### 4c: finální měření (sada `test`, 10 případů)

Nejlepší kombinace podle `dev` (gemini-3.5-flash-lite + v2, 100 %) a druhá nejlepší (gpt-oss-120b + v2, 93,3 %) spuštěné na `test` sadě:

| Model | Poskytovatel | Prompt | Sada | Validní JSON | Úplná shoda | model | Latence | Tokeny (vstup/výstup) |
|---|---|---|---|---|---|---|---|---|
| gemini-3.5-flash-lite | Gemini | v2 | test | 100 % | 90 % | 90 % | 1,44 s | 8870 / 547 |
| gpt-oss-120b | Groq | v2 | test | 100 % | 90 % | 90 % | 0,73 s | 8985 / 1805 |

Oba modely na `test` sadě selhaly na úplně stejném jediném případu (č. 18 – Mercedes-Benz C220 CDI) a stejným způsobem: vrátily `"model": "C220 CDI"` místo gold hodnoty `"C220"`. Při bližším pohledu je to spíš nejednoznačnost v pravidlech porovnávání než chyba modelu.
