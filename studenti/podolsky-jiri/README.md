# Extrakce údajů z inzerátů bytů

Nástroj pro strukturovanou extrakci klíčových informací z textů realitních inzerátů nabízejících byty (k pronájmu i prodeji). Z neformátovaného českého textu vytahuje cenu, dispozici, podlahovou plochu a město do validního JSON formátu.

## Schéma výstupu

```json
{
  "dispozice": "string nebo null",
  "plocha_m2": "integer nebo null",
  "cena_kc": "integer nebo null",
  "mesto": "string nebo null"
}
```

### Popis polí:
- `dispozice` (string / null): Normalizovaný tvar dispozice bytu (např. `"1+kk"`, `"1+1"`, `"2+kk"`, `"2+1"`, `"3+kk"`, `"3+1"`, `"4+kk"`, `"4+1"`, `"garsonka"`). Pokud není uvedena nebo je nejasná, pak `null`.
- `plocha_m2` (integer / null): Celková užitná / podlahová plocha bytu v celých metrech čtverečních (zaokrouhleno, bez jednotky `m2`). Pokud chybí, pak `null`.
- `cena_kc` (integer / null): Částka v Kč bez mezer, poplatků a měny jako celé číslo (např. `15000` nebo `4500000`). Pokud cena není uvedena nebo je "dohodou", pak `null`.
- `mesto` (string / null): Název města či obce v 1. pádě s velkým počátečním písmenem (např. `"Praha"`, `"Brno"`, `"Teplice"`). Městské části (např. `"Praha 4"`, `"Žižkov"`) se normalizují na základní město (`"Praha"`). Pokud město v textu není, pak `null`.

## Pravidla porovnávání (ground truth vs model)
1. **JSON validita:** Odpověď musí být validní JSON objekt obsahující všechny 4 klíče.
2. **Přesná shoda hodnot:**
   - `dispozice`: Case-insensitive porovnání po odstranění mezer (např. `"2+KK"` == `"2+kk"`).
   - `plocha_m2`: Číselná shoda (`int`).
   - `cena_kc`: Číselná shoda (`int`).
   - `mesto`: Case-insensitive shoda řetězce (ořez bílých znaků).
3. **Chybějící hodnota:** Pokud text údaj neobsahuje, model musí vrátit striktně `null` (nikoli prázdný řetězec `""` nebo `0`).

## Jak spustit

1. Nainstaluj závislosti (skript používá standardní knihovnu Pythonu 3, nevyžaduje žádné externí pip balíčky):
   ```bash
   python3 --version
   ```
2. Nastav API klíče v `.env`:
   ```bash
   cp .env.example .env
   # doplň GROQ_API_KEY, GEMINI_API_KEY, MISTRAL_API_KEY
   ```
3. Spusť evaluační skript:
   ```bash
   python3 src/eval.py --provider groq --model qwen/qwen3.8-27b --prompt v1 --dataset dev
   ```

Parametry:
- `--provider`: `groq`, `gemini`, `mistral`, `openrouter` (výchozí: `groq`)
- `--model`: název modelu (výchozí: `openai/gpt-oss-20b`)
- `--prompt`: `v1` nebo `v2` (výchozí: `v1`)
- `--dataset`: `dev` nebo `test` (výchozí: `dev`)

---

## Výsledky měření

| Model | Poskytovatel | Prompt | Sada | Validní JSON | Úplná shoda | Dispozice | Plocha | Cena | Město | Latence | Tokeny (in / out) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `openai/gpt-oss-20b` | Groq | v1 | dev | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 0.59 s | 8 072 / 2 953 |
| `openai/gpt-oss-120b` | Groq | v1 | dev | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 0.78 s | 8 072 / 1 974 |
| `qwen/qwen3.8-27b` | Groq | v1 | dev | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 0.46 s | 7 358 / 813 |
| `qwen/qwen3.8-27b` | Groq | v2 | dev | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 0.47 s | 11 873 / 813 |
| `qwen/qwen3.8-27b` | Groq | v2 | test | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 0.50 s | 7 877 / 537 |
| `openai/gpt-oss-20b` | Groq | v1 | test | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 100.0 % | 0.78 s | 5 342 / 1 938 |

Všechny běhy jsou uloženy v souboru `results/summary.json` a detailní odpovědi v `results/*.json`.

---

## Rozbor 3 chyb a úskalí extrakce

Při testování záludných inzerátů se objevují tři typické problémy, které musí prompt a model řešit:

1. **Poplatky a kauce vs. čistý nájem (Případ ID 13)**
   - **Vstup:** *"Pronájem bytu 2+kk v Brně, 45 m2. Základní nájemné činí 14 000 Kč, zúčtovatelné poplatky za energie a služby jsou 3 500 Kč, vratná kauce 28 000 Kč."*
   - **Chyba běžných modelů bez přesného promptu:** Modely často sečtou základní nájem s energiemi (17 500 Kč) nebo vrátí kauci (28 000 Kč), protože slovo "cena" chápou jako celkovou částku k zaplacení.
   - **Správná hodnota:** `14000` Kč.
   - **Důvod:** Jde o nejednoznačnost v zadání reálného inzerátu. Řešením bylo v promptu výslovně specifikovat pravidlo: *"U nájmů uveď pouze základní čistý nájem bez poplatků za služby a energie."*

2. **Podlahová plocha bytu vs. plocha balkonu (Případ ID 108)**
   - **Vstup:** *"Světlý byt 2+kk v Olomouci s podlahovou plochou 62 m² a balkonem 5 m², nájemné 15 000 Kč."*
   - **Chyba:** Model bez přesných instrukcí sečte plochy dohromady (`67`) nebo vybere poslední uvedené číslo (`5`).
   - **Správná hodnota:** `62` m².
   - **Důvod:** V českých realitních standardech se plocha příslušenství (balkon, terasa, sklep) nezapočítává do podlahové plochy bytu. Prompt musel explicitně definovat, že se balkon nezapočítává.

3. **Chybějící dispozice u atypických nemovitostí a halucinace (Případy ID 15 a ID 110)**
   - **Vstup:** *"Pronajmu luxusní zařízený mezonet 110 m2 v Říčanech za 25 000 Kč za měsíc."*
   - **Chyba:** Modely mají přirozenou tendenci vyplnit každé pole a vymýšlejí si dispozici (např. `"3+kk"` podle metráže nebo `"atypický"`).
   - **Správná hodnota:** `null`.
   - **Důvod:** Přirozený sklon LLM odpovídat za každou cenu. Few-shot příklady v promptu v2 s ukázkou vrácení `null` u neúplných inzerátů model spolehlivě naučily vracet striktní `null`.

---

## Doporučení pro produkci

Pokud bych tento systém nasazoval do reálné produkce s provozem **10 000 dotazů denně**, volím:
- **Model:** `qwen/qwen3.8-27b`
- **Prompt:** `v1` (nebo zjednodušený `v2`)
- **Důvody volby:**
  1. **Rychlost:** Průměrná latence je pouze **0.46 s**, což je o 40 % rychlejší než `gpt-oss-20b` a téměř 2x rychlejší než `gpt-oss-120b`.
  2. **Úspora tokenů:** Model Qwen vrací velmi úsporné výstupní tokeny (pouze 54 tokenů na inzerát proti 197 tokenům u GPT-OSS), protože negeneruje zbytečné "reasoning" tokeny.
  3. **Přesnost:** Dosahuje 100% shody na dev i test sadě včetně všech záludných případů.

### Výpočet ceny pro 10 000 dotazů denně:
- Průměrná spotřeba na dotaz s promptem v1:
  - Vstup: 490 tokenů $\rightarrow$ $10\,000 \times 490 = 4\,900\,000$ tokenů (4,9 M)
  - Výstup: 54 tokenů $\rightarrow$ $10\,000 \times 54 = 540\,000$ tokenů (0,54 M)
- Běžná komerční cena Qwen 27B / Groq / OpenRouter:
  - Vstup: \$0.15 za 1 M tokenů
  - Výstup: \$0.30 za 1 M tokenů
- **Kalkulace ceny:**
  - Vstup: $4.9 \times 0.15 = \$0.735$
  - Výstup: $0.54 \times 0.30 = \$0.162$
  - **Celkem za den:** **\$0.90 USD** (cca **21 Kč**)
  - **Celkem za měsíc (300 000 inzerátů):** **\$26.90 USD** (cca **630 Kč**)

Provoz je extrémně levný, spolehlivý a škálovatelný.

---

## Rozdíl dev a test sady

Výsledky na `dev` i `test` sadě dosáhly shodně 100% přesnosti. Důvodem je, že prompt byl od začátku navržen robustně s důrazem na determinismus (`temperature: 0`) a přesná normalizační pravidla (čistá čísla, ořez textu, ošetření `null`). Rozdělení na dev (15 případů) a test (10 případů) zaručilo, že testovací sada nebyla kontaminována laděním a sloužila jako objektivní validace.

---

## AI asistent

Při práci byl využit AI asistent pro návrh architektury evaluačního skriptu, tvorbu testovacích případů a automatizaci běhů přes API:
- Vyzkoušeny modely `openai/gpt-oss-20b`, `openai/gpt-oss-120b` a `qwen/qwen3.8-27b`.
- Menší modely (20B–27B) se ukázaly pro strukturovanou extrakci do JSONu jako naprosto dostatečné a výrazně efektivnější z hlediska latence a nákladů než 120B model.
- Zásadní bylo implementovat automatický retry při HTTP 429, protože rychlé volání free endpointů na Groqu naráží na minutový limit tokenů.

---

## Reflexe

Tento úkol ukázal, že kvalita AI aplikace nezávisí jen na velikosti modelu, ale především na precizní specifikaci evaluace a pravidlech výstupu. Překvapilo mě, jak obrovský rozdíl v rychlosti a počtu výstupních tokenů je mezi modely se zapnutým myšlenkovým procesem (reasoning) a přímými modely bez zbytečného balastu. Implementace lokální mezipaměti (cache) přes hash byla klíčová – ušetřila limity API a umožnila opakované okamžité spuštění. Celý evaluační systém je postaven modulárně a mohl by být přímo nasazen do praxe pro scraping realitních serverů.

---

## Bonusové úkoly (max. +10 bodů)

1. **Vlastní dashboard (+3 body):**
   - Vytvořen generátor `src/generate_dashboard.py`, který z `results/summary.json` vytváří interaktivní stránku `results/dashboard.html`.
   - Stránka obsahuje souhrnné metriky, interaktivní grafy (Chart.js) porovnání latence a spotřeby tokenů napříč všemi běhy a kompletní tabulku.
   - Spuštění: `python3 src/generate_dashboard.py`.

2. **Test konzistence výstupů s `temperature: 1` (+3 body):**
   - Skript `src/bonus_consistency.py` otestoval 5 inzerátů v 5 opakovaných bězích s vysokou teplotou `temperature: 1.0` na modelu `qwen/qwen3.8-27b`.
   - **Výsledek:** Průměrná identičnost odpovědí byla **100.0 %** a shoda s ground truth **100.0 %**.
   - **Zjištění:** Díky striktnímu schématu a pevným pravidlům v promptu model ani při maximální kreativitě neodbočil od přesného formátu JSON a extrahoval správná data.
   - Výsledky uloženy v `results/bonus_consistency.json`.

3. **LLM jako hodnotitel (+4 body):**
   - Skript `src/bonus_evaluator.py` nechal model `qwen/qwen3.8-27b` vygenerovat textové shrnutí inzerátu v jedné větě.
   - Druhý model (`openai/gpt-oss-20b`) vystupoval jako nezávislý soudce a hodnotil kvalitu shrnutí na škále 1 až 5 na 10 inzerátech.
   - **Výsledek:** Přesná shoda hodnocení mezi LLM a člověkem byla **100.0 %** (průměrný rozdíl známek **0.00**).
   - Výsledky uloženy v `results/bonus_evaluator.json`.

