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

## Fáze 5: Rozbor a závěr

### Rozbor 3 chyb

**1. Model spletl, co znamenají čísla napsaná jako slovo**

Vstup: *„Nazdar prodam oktavku, rv 2014, najeto poctivych dve ste pade, necham za sedesat, dohoda mozna"*

Model (gpt-oss-20b) odpověděl: nájezd `250` km, cena `600` Kč. Správně má být nájezd `250000` km, cena `60000` Kč.

Proč se spletl: Model vzal čísla doslova. I když jsem do promptu přidal přímo tenhle vzor, pořád to občas spletl – u malého modelu (20b) to vypadá na jeho limit, ne na chybu zadání. Zajímavý detail: na stejný dotaz jednou model odpověděl rovnou prázdně (bez JSONu), podruhé vrátil ten špatný výsledek – i při `temperature: 0` tedy odpověď není vždycky úplně stejná.

**2. Model (u všech tří testovaných modelů) ztratil kus označení auta**

Vstup: *„Bávo na prodej, 2010, najeto tři sta dvacet tisíc kilometrů, cena 180K, 320d."*

Modely odpověděly různě špatně: jeden `model` vůbec nenašel, druhý napsal jen `"3"`, třetí `"320"` (bez „d" na konci). Správně má být `"320d"`.

Proč: „320d" je ve větě schované úplně na konci, oddělené čárkou od zbytku, a značka je napsaná slangově. Žádný model si to nedokázal spojit dohromady. Tohle je chyba promptu, ne modelu – potvrdilo se to tím, že po úpravě promptu to začaly zvládat všechny tři.

**3. Spor o to, co vlastně patří do pole „model"**

Vstup: *„...Mercedes-Benz třídy C, model C220 CDI..."*

Model odpověděl `"C220 CDI"`, v mých gold datech mám `"C220"`.

Proč: tohle je nejspíš chyba v mé vlastní správné odpovědi, ne modelu. Text doslova říká „model C220 CDI", takže model se jen držel textu. Já jsem si předem řekl, že generační označení typu „VII" do pole nepatří, ale nikde jsem přesně nedefinoval, co dělat s označením motoru („CDI", „TDI" apod.). Je to hraniční případ, který bych příště definoval přesněji už v Fázi 1.

### Doporučení

Pro nasazení na 10 000 dotazů denně bych vybral **gemini-3.5-flash-lite s promptem v2**. Mělo nejlepší výsledky (100 % na dev, 90 % na test) a navíc generuje hodně krátké odpovědi, takže je i levné. Je sice o trochu pomalejší než modely na Groqu (~1,4 s místo ~0,8 s na dotaz), ale pro zpracování inzerátů na pozadí rozhoduje spíš přesnost a cena než pár desetin sekundy.

Cena: na OpenRouteru stojí placená verze `google/gemini-3.5-flash-lite` 0,30 $ za milion vstupních tokenů a 2,50 $ za milion výstupních tokenů. Z běhu na `test` sadě mi vyšlo v průměru 887 vstupních a 55 výstupních tokenů na jeden dotaz. Při 10 000 dotazech denně:

- vstup: 8 870 000 tokenů × 0,0000003 $ ≈ 2,66 $
- výstup: 550 000 tokenů × 0,0000025 $ ≈ 1,37 $
- **celkem zhruba 4 $ na den** (cca 95 Kč při kurzu 23,5 Kč/$)

### Rozdíl dev a test

Jo, liší se – lepší modely (120b, gemini) měly na `dev` sadě 93,3–100 %, na `test` sadě klesly na 90 %. `dev` sadu jsem používal na ladění promptu, takže se chování modelu na ni trochu „přizpůsobilo". `test` sada je oproti tomu sada, kterou model (a prompt) nikdy neviděl, takže ukazuje reálnější číslo. Rozdíl pár procent beru jako dobré znamení – nepřeučil jsem to na dev sadě moc.

### AI asistent

V OpenCode jsem si připojil Mistral, Google a Groq a nastavil defaultní model na `mistral/devstral-latest`. Hned na začátku jsem narazil na to, že PowerShell blokuje spouštění `.ps1` skriptů (vyřešil jsem to spuštěním `opencode.cmd` místo `opencode`). Později jsem v OpenCode zkoušel přepnout na `gemini-3.8-flash` – model se zacyklil na špatně naformátovaném volání nástroje a opakovaně generoval čím dál delší a delší vnořenou chybovou hlášku, musel jsem konverzaci zrušit a založit novou. Po přepnutí na DeepSeek V4.1 Flash (Free) už to fungovalo normálně.

Většinu samotného psaní kódu (eval skript, cache, porovnávací logika, hledání chyb u Mistral/Gemini API, návrh a úpravy promptů) jsem dělal s **Claude Code**, ne přímo v OpenCode – na delší, propojené úkoly s hledáním chyb napříč víc soubory mi přišel rychlejší a spolehlivější. Rozdíl mezi menším a větším modelem jsem nejvíc poznal přímo v evalu: `gpt-oss-20b` dělal chyby (čísla napsaná slovy, nejistota u slangu), které si desetinásobně větší `gpt-oss-120b` nedovolil.

### Reflexe

Nejvíc mě překvapilo, že i velké bezplatné modely dokážou selhat na docela banální drobnosti, jako je číslo napsané slovy nebo schované na konci věty – čekal jsem spíš chyby ve složitějších věcech. Taky mě zaskočilo, jak nestabilní dokáže být odpověď i při `temperature: 0` – stejný dotaz jednou vrátil prázdnou odpověď, podruhé normální JSON. Mistral a Gemini mi navíc několikrát spadly na rate limitu nebo přetížení serveru. Příště bych si testovací sadu promyslel ještě pečlivěji hned na začátku.Taky bych rovnou na začátku vyzkoušel víc modelů najednou místo postupného doplňování, ušetřilo by to čas.
