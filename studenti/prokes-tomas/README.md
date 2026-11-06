# Inzeráty aut: značka, model, rok, nájezd v km, cena

## Co nástroj dělá

Nástroj vezme text inzerátu na prodej auta a vytáhne z něj strukturované údaje do JSONu: značku, model, rok výroby, nájezd v km a cenu. Hodí se například na porovnávání nabídek z různých bazarů aut v jednotném formátu.

## Schéma výstupu

```json
{
  "znacka": "string",
  "model": "string",
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

## Pravidla porovnávání

- `znacka` a `model`: nerozlišuje se velikost písmen a přebytečné mezery na začátku/konci se ignorují (`"škoda"` = `"Škoda"` = `" Škoda "`).
- `rok`: musí sedět přesně jako číslo (ne jako text, tedy `2015`, ne `"2015"`).
- `najezd_km`: porovnává se jako číslo po normalizaci zápisu – mezery, tečky jako oddělovač tisíců a jednotka `km` se ignorují (`"150 000 km"` = `"150.000 km"` = `150000`).
- `cena`: porovnává se jako číslo po normalizaci zápisu – mezery, oddělovače tisíců a měna (`Kč`, `,-`) se ignorují (`"350 000 Kč"` = `"350000,-"` = `350000`).
- Pokud text daný údaj neobsahuje, očekávaná hodnota je `null` a jako správná se uzná jen `null` (ne prázdný řetězec nebo `0`).
