# Hlášení závad v učebně

## 1. Co nástroj dělá

Nástroj z textového hlášení závady vytěží její kategorii, prioritu a označení učebny. Výstup převádí do jednotného JSON formátu, aby bylo možné hlášení automaticky evidovat a porovnávat s očekávanými hodnotami. Pokud učebnu nelze z textu určit, vrátí hodnotu `null`.

## 2. Přesné schéma výstupu

Nástroj vrací právě tato tři pole:

```json
{
  "kategorie": "hardware | software | sit | elektrina | jine",
  "priorita": "nizka | stredni | vysoka",
  "ucebna": "string nebo null"
}
```

### Význam polí

| Pole | Typ | Význam |
|---|---|---|
| `kategorie` | enum / string | Druh hlášené závady. |
| `priorita` | enum / string | Závažnost závady a naléhavost jejího řešení. |
| `ucebna` | string nebo null | Označení učebny uvedené v hlášení; `null`, pokud ji nelze spolehlivě určit. |

### Povolené hodnoty

**`kategorie`:**
- `hardware` – fyzická závada počítače, monitoru, projektoru, klávesnice nebo jiného zařízení.
- `software` – chyba programu, operačního systému nebo aplikace.
- `sit` – nefunkční nebo omezené síťové či internetové připojení.
- `elektrina` – závada napájení, zásuvky, osvětlení nebo elektrického rozvodu.
- `jine` – problém, který nespadá do žádné z předchozích kategorií.

**`priorita`:**
- `nizka` – drobná závada, která zásadně neomezuje používání zařízení nebo učebny.
- `stredni` – závada omezuje práci, ale existuje náhradní řešení nebo se netýká celé učebny.
- `vysoka` – zařízení nebo důležitá část učebny je nepoužitelná, problém zasahuje více zařízení, nebo hrozí bezpečnostní riziko.

## 3. Pravidla porovnávání

Při vyhodnocování se očekávaná odpověď (`expected`) porovnává s výstupem nástroje podle těchto pravidel:

1. **Malá a velká písmena:** U textových hodnot se nerozlišují. Například `Hardware` a `hardware` se považují za shodné.
2. **Mezery:** Odstraní se mezery na začátku a konci hodnoty. Více mezer uvnitř textu se sjednotí na jednu.
3. **Kategorie a priorita:** Po normalizaci musí hodnota přesně odpovídat jedné z povolených hodnot. Významově podobná, ale nepovolená hodnota se nepovažuje za správnou.
4. **Učebna:** Označení se porovnává jako text po odstranění krajních a sjednocení vícenásobných mezer. Například `204` a ` 204 ` jsou shodné. Hodnoty `204` a `205` shodné nejsou.
5. **Chybějící učebna:** Pokud hlášení neobsahuje dostatek informací pro určení učebny, správná hodnota je JSON `null`. Řetězec `"null"` ani prázdný řetězec nejsou totéž co `null`.
6. **Číselné a slovní označení učebny:** Slovní zápis se převede na číslo pouze tehdy, pokud jednoznačně označuje číslo učebny. Například „patnáct set“ znamená `1500`.
7. **Nejednoznačnost:** Pokud text uvádí více učeben a není jasné, které se závada týká, použije se `null`.

## 4. Testovací data

Testovací sada obsahuje celkem **25 případů** (12 z nich je označeno jako záludných `"tezky": true`) a je striktně rozdělena do dvou souborů ve složce `data/`:

- `data/dev.jsonl` – 15 případů určených pro ladění promptu.
- `data/test.jsonl` – 10 případů určených výhradně pro závěrečné vyhodnocení (během ladění promptu se nepoužívají).

Struktura každého záznamu:

```json
{
  "id": 1,
  "input": "Dobrý den, v učebně 204 nejde zapnout projektor. Za hodinu tam máme maturitní prezentace.",
  "expected": {
    "kategorie": "hardware",
    "priorita": "vysoka",
    "ucebna": "204"
  },
  "tezky": false
}
```

Záludné případy pokrývají:
- Chybějící učebnu (`null`), např. ID 4, 6, 11, 20
- Slovní označení učebny („patnáct set“ $\rightarrow$ `1500`), např. ID 8
- Ironické vyjádření (závada popsaná pochvalou), např. ID 9, 19
- Dotazy bez závady (nespadá pod incident $\rightarrow$ `jine`), např. ID 13
- Závadu v jiné místnosti (v kabinetu vedle učebny $\rightarrow$ `ucebna: null`), např. ID 14
- Souběh dvou různých závad (např. zásuvka a Wi-Fi), např. ID 21

## 5. Jak projekt spustit

Projekt je napsán v **čistém Pythonu 3** bez jakýchkoliv externích knihoven (používá pouze standardní knihovnu `urllib`, `json`, `hashlib` apod.). Nevyžaduje spouštět `pip install`.

### Příprava prostředí
1. Zkopíruj vzorový soubor konfigurace a doplň své API klíče:
   ```bash
   cp .env.example .env
   ```
   (Soubor `.env` obsahuje proměnné `GROQ_API_KEY`, `NVIDIA_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY`).

### Spuštění evaluace
Skript `src/eval.py` lze spustit s těmito parametry:

```bash
# Spuštění výchozího běhu (Groq + GPT OSS 20B, prompt v1, dev sada):
python src/eval.py --model openai/gpt-oss-20b --provider groq --prompt v1 --dataset dev

# Spuštění s modelem Qwen na testovací sadě s promptem v2:
python src/eval.py --model qwen/qwen3.8-27b --provider groq --prompt v2 --dataset test

# Vypnutí mezipaměti (vynucení nových API dotazů):
python src/eval.py --model openai/gpt-oss-20b --provider groq --prompt v1 --dataset dev --no-cache
```

Výsledky se automaticky zaznamenávají do `results/summary.json` a surové odpovědi s tokeny do `results/*.json`.

### Spuštění bonusových skriptů
```bash
# Test stability výstupů (5 případů 5krát s temperature: 1.0):
python src/consistency_test.py

# Vygenerování HTML dashboardu:
python src/generate_dashboard.py
```

---

## 6. Fáze 4: Výsledky experimentů

Všechny výsledky níže byly naměřeny skriptem `src/eval.py` s `temperature: 0` a odpovídají souboru `results/summary.json`.

| Model | Poskytovatel | Prompt | Sada | Validní JSON | Úplná shoda | Kategorie | Priorita | Učebna | Latence | Tokeny (vstup / výstup) |
|---|---|---|---|---|---|---|---|---|---|---|
| `openai/gpt-oss-20b` | Groq | v1 | dev | **100.0 %** | 86.7 % | 93.3 % | 93.3 % | 100.0 % | 0.67 s | 8 518 / 3 800 |
| `qwen/qwen3.8-27b` | Groq | v1 | dev | **100.0 %** | 86.7 % | 100.0 % | 86.7 % | 100.0 % | 0.40 s | 7 924 / 523 |
| `google/gemma-4-31b-it` | NVIDIA | v1 | dev | 93.3 % | 86.7 % | 86.7 % | 93.3 % | 93.3 % | 7.23 s | 7 289 / 480 |
| `openai/gpt-oss-120b` | Groq | v1 | dev | **100.0 %** | 73.3 % | 93.3 % | 80.0 % | 100.0 % | 0.73 s | 8 518 / 2 975 |
| `openai/gpt-oss-20b` | Groq | v2 | dev | **100.0 %** | 80.0 % | 93.3 % | 86.7 % | 100.0 % | 0.65 s | 14 368 / 3 727 |
| `qwen/qwen3.8-27b` | Groq | v2 | dev | **100.0 %** | **93.3 %** | 100.0 % | 93.3 % | 100.0 % | **0.36 s** | 13 924 / 523 |
| `qwen/qwen3.8-27b` | Groq | v2 | test | **100.0 %** | 80.0 % | 100.0 % | 80.0 % | 100.0 % | **0.32 s** | 9 280 / 347 |
| `openai/gpt-oss-20b` | Groq | v1 | test | **100.0 %** | **90.0 %** | 100.0 % | 90.0 % | 100.0 % | 0.73 s | 5 684 / 2 885 |
| `openai/gpt-oss-20b` | Groq | v2 | test | **100.0 %** | 70.0 % | 100.0 % | 70.0 % | 100.0 % | 0.88 s | 9 584 / 4 130 |

---

## 7. Fáze 5: Rozbor a závěr

### 1. Rozbor 3 konkrétních chyb

#### Chyba 1: Dotaz bez závady (ID 13, dev sada, prompt v1)
- **Vstup:** *„Dobrý den, chtěl bych se zeptat, kdy bude v učebně 12 instalován nový software. Současný funguje bez problémů.“*
- **Očekáváno:** `{"kategorie": "jine", "priorita": "nizka", "ucebna": "12"}`
- **Model vrátil (`openai/gpt-oss-20b` v1):** `{"kategorie": "software", "priorita": "nizka", "ucebna": "12"}`
- **Příčina chyby:** V textu se dvakrát vyskytuje slovo „software“. Model v promptu v1 zachytil klíčové slovo a mechanicky přiřadil kategorii `software`, aniž by zohlednil sémantiku – v textu není hlášena žádná závada, stávající stav funguje. V promptu v2 jsme do definice `jine` přidali výslovné pravidlo: *„nespadá do technických závad nebo dotazy, kde nic není rozbité“*, což u modelu Qwen chybu úspěšně eliminovalo.

#### Chyba 2: Závažnost modré obrazovky (ID 6, dev sada, prompt v1)
- **Vstup:** *„Na školním počítači se po aktualizaci stále zobrazuje modrá obrazovka.“*
- **Očekáváno:** `{"kategorie": "software", "priorita": "stredni", "ucebna": null}`
- **Model vrátil (`openai/gpt-oss-20b` v1):** `{"kategorie": "software", "priorita": "vysoka", "ucebna": null}`
- **Příčina chyby:** Model vyhodnotil modrou smrt (BSOD) jako kritickou havárii (`vysoka`). Dle naší definice priorit je však `vysoka` vyhrazena pro výpadek celé učebny, bezprostřední ohrožení maturitních zkoušek nebo bezpečnostní riziko (požár, kouř). Porucha jednoho počítače je pouze `stredni`. Šlo o hraniční interpretaci závažnosti, kdy model preferoval bezpečnější (vyšší) závažnost.

#### Chyba 3: Souběh závad a podcenění rizika elektroinstalace (ID 21, test sada, prompt v2)
- **Vstup:** *„Dobrý den, v učebně 2 je vadná zásuvka a zároveň nefunguje připojení k Wi-Fi.“*
- **Očekáváno:** `{"kategorie": "elektrina", "priorita": "vysoka", "ucebna": "2"}`
- **Model vrátil (`qwen/qwen3.8-27b` v2):** `{"kategorie": "elektrina", "priorita": "stredni", "ucebna": "2"}`
- **Příčina chyby:** Model správně určil, že vadná zásuvka je primární kategorií (`elektrina`), ale v prioritě zvolil `stredni`. Protože v hlášení nebyla výslovně uvedena slova jako „kouř“ nebo „jiskření“, model nepovažoval zásuvku za akutní ohrožení bezpečnosti. Správná odpověď počítá s tím, že nefunkční/poškozená zásuvka ve třídě plné žáků představuje bezpečnostní riziko, a proto vyžaduje vysokou prioritu.

---

### 2. Doporučení pro produkční nasazení (10 000 dotazů denně)

Pro produkční nasazení školního helpdesku doporučuji model **`qwen/qwen3.8-27b`** (případně ekvivalentní Qwen 2.5 32B / 72B na OpenRouteru / Groqu) s promptem **`v2`**.

**Důvody:**
1. **Rychlost:** Průměrná latence je pouhých **0.32 až 0.36 sekundy**, což je dvakrát rychlejší než GPT OSS 20B a dvacetkrát rychlejší než Gemma na NVIDIA NIM.
2. **Kvalita a validita:** 100% validní JSON bez jediného pádu a 100% přesnost na extrakci učebny a kategorie.
3. **Úspora tokenů:** Model negeneruje zbytečné myšlenkové řetězce ani tokenovou vatu – na výstupu spotřeboval pouze 35 tokenů na požadavek (oproti cca 250–290 tokenům u GPT OSS 20B reasoning).

#### Finanční kalkulace (10 000 dotazů denně):
Dle naměřených dat:
- Průměrná délka dotazu včetně systémového promptu: cca **928 vstupních tokenů**
- Průměrná délka odpovědi: cca **35 výstupních tokenů**
- Za 10 000 dotazů:
  - **Vstup:** $10\,000 \times 928 = 9\,280\,000$ tokenů (~9.28 milionu)
  - **Výstup:** $10\,000 \times 35 = 350\,000$ tokenů (~0.35 milionu)

Ceny placených variant na OpenRouteru (např. Qwen 2.5 32B / Llama 3.3 70B):
- Vstup: **\$0.20 za 1M tokenů**
- Výstup: **\$0.60 za 1M tokenů**

$$ \text{Cena za den} = (9.28 \times 0.20) + (0.35 \times 0.60) = 1.856 + 0.21 = \mathbf{2.07\ \text{USD/den}} $$

Při přepočtu na českou měnu činí provoz **cca 48 Kč denně** za kompletní automatické zpracování 10 000 hlášení, což je zanedbatelná částka.

---

### 3. Rozdíl mezi dev a test sadou

Na vývojové sadě (`dev`) dosáhl Qwen v2 úspěšnosti **93.3 %**, zatímco na testovací sadě (`test`) dosáhl **80.0 %** (u GPT OSS 20B s v1 to bylo 86.7 % na dev vs 90.0 % na test).
Rozdíl pramení ze složení záludných případů:
- Vývojová sada obsahovala specifické chytáky na slovní čísla („patnáct set“) a dotazy bez poruchy, na které byl prompt v2 přímo vyladěn.
- Testovací sada přinesla nové typy nejednoznačností, např. kombinaci více závad v jedné větě (zásuvka + Wi-Fi) nebo subtilnější popis hardwarových potíží (prasklé sklo dotykové tabule, kde dotyk funguje), kde se projevila přirozená subjektivita v klasifikaci priority.
Tento rozdíl jasně demonstruje význam dělení dat: ladění na dev sadě může vést k mírnému přizpůsobení formulacím v dev sadě, a teprve test sada ukáže reálnou generalizační schopnost.

---

### 4. Zkušenosti s AI asistentem

Během práce jsem využíval konfigurovaného asistenta OpenCode a DeepMind Antigravity:
- **Použité modely:** Primárně byl v konfiguraci `opencode.json` nastaven `mistral/devstral-latest`, doplňkově testovány modely na Groqu a NVIDIA NIM.
- **S čím asistent pomohl:** Rychle sestavil kostru evaluačního skriptu v Pythonu, implementoval robustní retry mechanismus pro HTTP 429 rate limity a připravil vizualizační HTML dashboard.
- **Kde selhal / limity:** Menší modely a free endpointy měly tendenci narážet na přísné minutové limity (Groq cca 8 000 tokenů/min), u NVIDIA NIM docházelo k timeoutům (Gemma měla latenci přes 7 sekund a jeden dotaz vypršel). Velké modely (např. GPT OSS 120B) paradoxně nebyly v přesnosti lepší než kompaktnější Qwen 27B, ale spotřebovávaly násobně více tokenů pro reasoning.

---

### 5. Reflexe

Projekt mi prakticky ukázal, že spoléhat se na „dojem“ z jednoho či dvou dotazů je v AI vývoji fatální chyba. Teprve rigorózní evaluační sada odhalila, že model často tápe v prioritách nebo se nechá zmást pouhou přítomností klíčového slova (např. slovo „software“ v běžném dotazu na termín instalace). Velmi mě překvapilo, jak obrovský rozdíl v efektivitě existuje mezi modely: zatímco Qwen 3.8-27B dokázal vrátit bezchybný JSON za 0.3 sekundy s minimem tokenů, jiné modely potřebovaly stovky tokenů na interní uvažování a dosáhly horších výsledků. Pozitivně hodnotím implementaci mezipaměti (cache), která dramaticky urychlila opakované ladění a ušetřila API kvóty. Pokud bych projekt dělal znovu, definoval bych hranice priorit ještě přísněji a do schématu přidal pole pro krátké odůvodnění (`duvod`), které by umožnilo lépe diagnostikovat rozhodovací proces modelu.

---

## 8. Bonusy

### Bonus 1: Test konzistence (temperature: 1.0)
Skript `src/consistency_test.py` spustil 5 testovacích případů opakovaně 5krát s nastavením `temperature: 1.0`:
- **Výsledek:** U **60 % případů** (3 z 5) byla odpověď naprosto deterministická a stabilní ve všech 5 bězích.
- **Nestabilní případy:** U případu ID 3 (výpadek sítě) a ID 4 (blikající monitor bez učebny) model při vyšší teplotě osciloval v určení priority mezi `stredni` a `vysoka`. To potvrzuje, že pro extrakční a klasifikační úlohy je parametr `temperature: 0` klíčový pro stabilitu a reprodukovatelnost.
- Podrobná data jsou uložena v `results/consistency_results.json`.

### Bonus 2: Vlastní interaktivní HTML dashboard
V souboru `results/dashboard.html` byl vygenerován přehledný vizuální dashboard (generovaný skriptem `src/generate_dashboard.py`):
- KPI karty s klíčovými metrikami (nejlepší model, průměrná validita JSON, nejnižší latence)
- Srovnávací sloupcové grafy úspěšnosti modelů a latence
- Detailní tabulka všech běhů s barevným odlišením úspěšnosti a indikátory přesnosti pro jednotlivá pole
- Pro zobrazení stačí otevřít soubor `results/dashboard.html` v libovolném webovém prohlížeči.
