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
