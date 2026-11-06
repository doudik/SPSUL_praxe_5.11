# Extrakce strukturovaných dat z bug reportů

## Popis úlohy
Nástroj slouží k automatickému zpracování a strukturování hlášení chyb (bug reportů) od uživatelů a testerů do formátu JSON. Z nestrukturovaného textu v češtině extrahuje zasaženou komponentu systému, odhadnutou závažnost problému, informaci o reprodukovatelnosti a případnou konkrétní chybovou hlášku nebo chybový kód. Usnadňuje tím třídění (triage) hlášenek a jejich automatické směrování do správného týmu.

## Schéma výstupu (JSON)

Každý výstup modelu musí být validní JSON objekt s následující strukturou:

```json
{
  "komponenta": "frontend | backend | databaze | auth | platby | jine",
  "zavaznost": "nizka | stredni | vysoka | kriticka",
  "reprodukovatelny": true,
  "chybova_hlaska": "string nebo null"
}
```

### Popis jednotlivých polí:
- `komponenta` (string, povinné): Jedna z hodnot:
  - `frontend`: Problémy s UI, tlačítky, rozložením, zobrazením v prohlížeči, CSS, formuláři na webu.
  - `backend`: Chyby API, serverové timeouty, padání backend služeb, výpočetní chyby.
  - `databaze`: Chyby dotazů, zámky, neukládání dat, migrace, spojení s DB.
  - `auth`: Přihlašování, registrace, obnova hesla, oprávnění, tokeny, 2FA.
  - `platby`: Platební brána, zpracování plateb, fakturace, košík při placení.
  - `jine`: Ostatní nebo obecné chyby, které nelze jednoznačně zařadit.
- `zavaznost` (string, povinné): Jedna z hodnot:
  - `nizka`: Kosmetické vady, překlepy, drobné vizuální glitche bez vlivu na funkčnost.
  - `stredni`: Funkce nepracuje optimálně, ale existuje náhradní řešení (workaround), aplikace nepadá.
  - `vysoka`: Klíčová funkce nefunguje více uživatelům, blokuje běžnou práci.
  - `kriticka`: Celý systém nebo klíčová služba je nedostupná (výpadek, ztráta dat, bezpečnostní incident).
- `reprodukovatelny` (boolean nebo null):
  - `true`: Pokud text uvádí, že se chyba děje opakovaně, vždy, nebo uvádí kroky k reprodukci.
  - `false`: Pokud text uvádí, že se chyba stala jen jednou a znovu se nepodařilo nasimulovat.
  - `null`: Pokud v textu není o reprodukovatelnosti žádná zmínka.
- `chybova_hlaska` (string nebo null):
  - `string`: Přesné nebo zkrácené znění chybové zprávy, stack trace nebo HTTP status kódu (např. `"500 Internal Server Error"`, `"TypeError: undefined is not a function"`, `"ERR_CONNECTION_REFUSED"`).
  - `null`: Pokud v textu žádná konkrétní chybová hláška ani kód uvedeny nejsou.

---

## Pravidla porovnávání (Evaluation Rules)

Odpověď modelu je porovnávána s referenční hodnotou (*gold standard*) pole po poli:

1. **`komponenta`**:
   - Porovnání řetězců case-insensitive, s oříznutím bílých znaků (`strip().lower()`).
   - Musí přesně odpovídat jedné z definovaných kategorií.
2. **`zavaznost`**:
   - Porovnání řetězců case-insensitive, s oříznutím bílých znaků (`strip().lower()`).
   - Musí přesně odpovídat jedné z definovaných kategorií.
3. **`reprodukovatelny`**:
   - Striktní typová i hodnotová shoda (`true` / `false` / `null`).
   - V případě, že model vrátí string `"true"` / `"false"`, parser provede normalizaci na boolean.
4. **`chybova_hlaska`**:
   - Pokud je referenční hodnota `null`, model musí vrátit `null` (nebo prázdný řetězec, který je normalizován na `null`).
   - Pokud je referenční hodnota string: porovnává se case-insensitive; shoda je uznána, pokud extrahovaný text odpovídá nebo obsahuje klíčovou část chybového kódu/hlášky.

---

## Testovací sada (Fáze 2)

Sada obsahuje celkem 25 testovacích případů ve formátu JSONL, rozdělených podle zadání na:
- `data/dev.jsonl`: 15 případů (ID 1–15) určených pro ladění promptu.
- `data/test.jsonl`: 10 případů (ID 16–25) určených pro finální evaluační měření (nedotčeno při vývoji).

### Záludné případy (`tezky: true`)
Sada obsahuje 10 záludných případů (5 v dev, 5 v test) pokrývajících:
- **Chybějící údaje (`null`)**: Případy bez explicitní chybové hlášky nebo bez zmínky o reprodukovatelnosti (např. ID 6, 13, 22).
- **Dva systémy v jednom textu / zavádějící kontext**: Uživatel kliká v UI nebo provádí přihlašování, ale skutečným kořenovým problémem je pád databáze nebo transakce (např. ID 9, 21).
- **Překlepy, hovorový styl a slang**: Rychle sepsané hlášení s chybějící diakritikou a slangem (např. ID 8).
- **Ironie a sarkasmus**: Stížnost se sarkastickým tónem (např. ID 7, 19).
- **Nezařaditelná komponenta (`jine`)**: Hlášení problémů mimo standardní softwarové vrstvy, např. tiskárna v kanceláři nebo přehřátí racku v serverovně (např. ID 10, 24).
- **Chybový kód v textu**: Extrakce stavových kódů a hlášení (např. ID 20).

---

## Návod ke spuštění (Fáze 0)

Skript je napsán v čistém Pythonu bez nutnosti instalovat externí knihovny (využívá standardní knihovnu).

### Konfigurace prostředí
1. V této složce vytvoř soubor `.env` (pokud ještě nemáš) ze vzoru `.env.example`:
   ```bash
   cp .env.example .env
   ```
2. Doplň do `.env` své API klíče (např. `GROQ_API_KEY`).

### Spuštění evaluace
```bash
python src/eval.py --provider groq --model openai/gpt-oss-120b --dataset dev --prompt v1
```

---

## Výsledky experimentů (Fáze 4)

### 4a: Porovnání modelů na `dev` sadě (prompt `v1`)
Pro srovnání byly vybrány 3 modely různých velikostí a architektur na infrastruktuře Groq:
- **`openai/gpt-oss-20b`**: menší open-source model (~20 mld. parametrů).
- **`openai/gpt-oss-120b`**: velký open-source model (120 mld. parametrů).
- **`qwen/qwen3.8-27b`**: moderní vícejazyčný model střední velikosti (27 mld. parametrů).

Nejlepších výsledků dosáhl model **Qwen 3.8 27B** s úplnou shodou **73,3 %** a nejnižší latencí (0,49 s).

### 4b: Vylepšení promptu (`prompts/v2.txt`)
Z rozboru chyb promptu `v1` vyplynulo, že modely nejčastěji chybovaly v rozlišení jemných hranic pole `zavaznost` (např. záměna `vysoka` a `kriticka`) a v určení `reprodukovatelny` při plošných výpadcích.
V promptu `v2` byly aplikovány následující úpravy:
1. **Few-shot příklady**: Doplněny 3 kompletně vyřešené syntetické příklady (mimo testovací sadu) demonstrující odlišení závažností a práci s hodnotami `null`.
2. **Přesnější definice závažnosti**: Výslovně stanoveno, že `kriticka` znamená plošný výpadek či bezpečnostní havárii, zatímco výpadek jedné funkce (např. Google SSO) je `vysoka`.
3. **Pravidla pro kořenovou příčinu**: Zdůrazněno určení komponenty dle skutečné technické příčiny (např. selhání DB transakce při kliku v UI patří do `databaze`).

Na `dev` sadě dosáhl model **Qwen 27B** s promptem `v2` **100,0% úplné shody** (15/15 případů správně).

### 4c: Finální měření na `test` sadě
Vítězná konfigurace (`qwen/qwen3.8-27b` + `v2`) a druhá srovnávací konfigurace (`v1`) byly vyhodnoceny na dosud neviděné testovací sadě `data/test.jsonl`:
- S promptem `v1` dosáhl model na testovací sadě úplné shody **50,0 %**.
- S vylepšeným promptem `v2` dosáhl model úplné shody **80,0 %** (zlepšení o +30 procentních bodů na neviděných datech).

### Souhrnná tabulka všech běhů

| Model | Poskytovatel | Prompt | Sada | Validní JSON | Úplná shoda | Pole „komponenta“ | Pole „závažnost“ | Pole „reprodukovatelný“ | Pole „chybová hláška“ | Latence | Tokeny (vstup / výstup) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `openai/gpt-oss-20b` | Groq | v1 | dev | 100 % | 60,0 % | 100 % | 66,7 % | 93,3 % | 100 % | 0,81 s | 14 197 / 5 540 |
| `openai/gpt-oss-120b` | Groq | v1 | dev | 100 % | 60,0 % | 100 % | 66,7 % | 93,3 % | 100 % | 1,38 s | 14 197 / 3 900 |
| `qwen/qwen3.8-27b` | Groq | v1 | dev | 100 % | 73,3 % | 100 % | 80,0 % | 93,3 % | 100 % | 0,49 s | 13 627 / 838 |
| **`qwen/qwen3.8-27b`** | **Groq** | **v2** | **dev** | **100 %** | **100,0 %** | **100 %** | **100,0 %** | **100 %** | **100 %** | **0,69 s** | **20 587 / 839** |
| `qwen/qwen3.8-27b` | Groq | v1 | test | 100 % | 50,0 % | 100 % | 60,0 % | 90,0 % | 100 % | 0,56 s | 9 139 / 566 |
| **`qwen/qwen3.8-27b`** | **Groq** | **v2** | **test** | **100 %** | **80,0 %** | **100 %** | **90,0 %** | **90,0 %** | **100 %** | **0,63 s** | **13 779 / 567** |

---

## Rozbor chyb a reflexe (Fáze 5)

### 1. Rozbor 3 konkrétních chyb z měření

#### Chyba 1: Případ #21 (Sada `test`, model `qwen/qwen3.8-27b`, prompt `v2`)
- **Vstup:**  
  *„Při pokusu o přihlášení do aplikace uživatel zadá správné údaje, ale namísto přihlášení spadne spojení s databází a v logu se objeví: 'MongoServerError: connection pool closed'. Zkoušeno opakovaně u více účtů.“*
- **Model vrátil:**  
  `{"komponenta": "databaze", "zavaznost": "kriticka", "reprodukovatelny": true, "chybova_hlaska": "MongoServerError: connection pool closed"}`
- **Správná odpověď (gold):**  
  `{"komponenta": "databaze", "zavaznost": "vysoka", "reprodukovatelny": true, "chybova_hlaska": "MongoServerError: connection pool closed"}`
- **Důvod neshody:**  
  Model správně detekoval kořenovou komponentu (`databaze`), reprodukovatelnost i chybovou hlášku, ale spletl se v poli `zavaznost`. Model vyhodnotil uzavřený connection pool v MongoDB jako `kriticka`, protože bez DB spojení je aplikace prakticky nepoužitelná a nikdo se nepřihlásí. V našich pravidlech jsme však pro `vysoka` definovali stav, kdy klíčová funkce (přihlašování) nefunguje více lidem, zatímco `kriticka` byla vymezena pro kompletní pád celého produkčního prostředí. Šlo o jemnou hranici mezi definicemi, kde je úsudek modelu technicky pochopitelný.

#### Chyba 2: Případ #24 (Sada `test`, model `qwen/qwen3.8-27b`, prompt `v2`)
- **Vstup:**  
  *„Klimatizace v centrální serverovně hlásí chybový kód 'E-401 Overheat Warning' a teplota v racku stoupla na nebezpečných 38 stupňů. Senzor pípá nepřetržitě, hrozí okamžité nouzové vypnutí serverů.“*
- **Model vrátil:**  
  `{"komponenta": "jine", "zavaznost": "kriticka", "reprodukovatelny": null, "chybova_hlaska": "E-401 Overheat Warning"}`
- **Správná odpověď (gold):**  
  `{"komponenta": "jine", "zavaznost": "kriticka", "reprodukovatelny": true, "chybova_hlaska": "E-401 Overheat Warning"}`
- **Důvod neshody:**  
  Model vrátil `reprodukovatelny: null` místo očekávaného `true`. V hlášení je uvedeno, že *„senzor pípá nepřetržitě“*, což lidský hodnotitel chápe jako trvající, reprodukovatelný incident. LLM však hledalo obvyklou softwarovou formulaci kroků k reprodukci (např. *„dělá to pokaždé při kliknutí“*). Protože šlo o fyzický alarm klimatizace bez explicitního popisu testovacího postupu, model opatrně vrátil `null`. Jde zčásti o nejednoznačnost v zadání u ne-softwarových hlášení.

#### Chyba 3: Případ #7 (Sada `dev`, model `openai/gpt-oss-20b`, prompt `v1`)
- **Vstup:**  
  *„No to je fakt nádhera, tmavý režim jste vyřešili geniálně: černé písmo na černém pozadí v celém nastavení profilu. Kdo to má proboha luštit? Žádná chyba nevyskočí, prostě skvělý design. Dělá to pokaždé, když přepnu přepínač na dark mode.“*
- **Model vrátil:**  
  `{"komponenta": "frontend", "zavaznost": "nizka", "reprodukovatelny": true, "chybova_hlaska": null}`
- **Správná odpověď (gold):**  
  `{"komponenta": "frontend", "zavaznost": "stredni", "reprodukovatelny": true, "chybova_hlaska": null}`
- **Důvod neshody:**  
  Menší model GPT-oss-20b neporozuměl ironii a nadsázce v textu (*„No to je fakt nádhera, tmavý režim jste vyřešili geniálně“*). Problém vyhodnotil jako pouhý kosmetický barevný glitch v CSS (`nizka`), ačkoli černé písmo na černém pozadí kompletně znemožňuje čtení a ovládání profilu v tmavém režimu (s nutností přepnout do světlého režimu jako workaround $\rightarrow$ `stredni`). Tuto chybu ve verzi `v2` vyřešily až explicitní few-shot příklady.

---

### 2. Doporučení pro produkci a odhad nákladů

Pokud by měl být tento nástroj nasazen do reálné produkce s provozem **10 000 požadavků denně**, jednoznačně doporučuji kombinaci:
- **Model:** `qwen/qwen3.8-27b`
- **Prompt:** `prompts/v2.txt`

**Důvody volby:**
1. **Přesnost:** Dosahuje 100% úplné shody na dev sadě a 80% na testovací sadě, s 100% validitou JSON výstupu a 100% přesností v extrakci komponenty i chybové hlášky.
2. **Rychlost (latence):** Průměrná latence činí pouze **0,63 s** na požadavek (oproti 1,38 s u 120B modelu), což zajišťuje okamžitou odezvu při triage v reálném čase.
3. **Efektivita tokenů:** Model je úsporný a nevytváří zbytečné halucinace ve výstupu (průměrně pouze 57 výstupních tokenů na požadavek).

#### Výpočet nákladů pro 10 000 dotazů denně:
Na platformě **OpenRouter** je model `qwen/qwen3.8-27b` oceněn sazbami:
- **Vstup (Prompt):** $0{,}150$ za 1 000 000 tokenů ($0{,}15 / M tokenů)
- **Výstup (Completion):** $1{,}875$ za 1 000 000 tokenů ($1{,}875 / M tokenů)

Z našich reálných naměřených dat (běh `v2` na test sadě):
- Průměrný počet vstupních tokenů na 1 dotaz: $1\,378$ tokenů
- Průměrný počet výstupních tokenů na 1 dotaz: $57$ tokenů

Pro 10 000 dotazů denně spotřebujeme:
- **Vstupní tokeny celkem:** $10\,000 \times 1\,378 = 13\,780\,000$ tokenů = **13,78 M tokenů**
- **Výstupní tokeny celkem:** $10\,000 \times 57 = 570\,000$ tokenů = **0,57 M tokenů**

Finanční náklady:
$$\text{Náklady za vstup} = 13{,}78 \times \$0{,}150 = \$2{,}067$$
$$\text{Náklady za výstup} = 0{,}57 \times \$1{,}875 = \$1{,}069$$
$$\mathbf{\text{Celkové denní náklady (10 000 dotazů)}} = \$2{,}067 + \$1{,}069 = \mathbf{\$3{,}14}\ \text{(cca 72 Kč/den)}$$
$$\mathbf{\text{Celkové měsíční náklady (300 000 dotazů)}} = 30 \times \$3{,}14 = \mathbf{\$94{,}20}\ \text{(cca 2 160 Kč/měsíc)}$$

Provoz takto přesného automatického třídění bug reportů je extrémně ekonomický.

---

### 3. Rozdíl mezi dev a test sadou

- Na sadě **`dev`** dosáhl nejlepší model s promptem `v2` **100,0 %** úplné shody (15 z 15 případů).
- Na sadě **`test`** dosáhl tentýž model s promptem `v2` **80,0 %** úplné shody (8 z 10 případů).

**Proč se výsledky liší?**
1. **Efekt adaptace na dev data:** Prompt `v2` byl vytvořen na základě rozboru chyb zjištěných na `dev` sadě. Zpřesněné definice a few-shot příklady byly zacíleny na konkrétní nejasnosti, které se projevily při ladění na `dev`.
2. **Přirozená generalizace na neviděná data:** Sada `test` obsahovala nové, předem neviděné varianty záludných hlášení (např. případ selhání DB poolu v procesu přihlašování nebo alarm klimatizace v serverovně). Pokles přesnosti o 20 procentních bodů je v souladu s teorií strojového učení – přesně demonstruje, proč se testovací sada musí striktně držet stranou až do finálního měření, abychom nezískali nerealisticky optimistický odhad úspěšnosti.

---

### 4. Zkušenost s AI asistentem

- **K čemu byl asistent využit:**  
  AI asistent asistoval při formulaci testovacích scénářů (vymýšlení pestrých hlášení z různých IT oblastí), návrhu architektury skriptu `eval.py` s integrovanou mezipamětí a backoff retry pro rate limity, i při ladění textu promptu `v2`.
- **Pozorované rozdíly mezi modely:**  
  Menší modely (~20B) měly znatelné potíže s interpretací ironických textů a inklinovaly k chybám v jemnějších sémantických kategoriích (`zavaznost`). Naopak větší či novější modely (Qwen 27B) vykázaly 100% spolehlivost v dodržování JSON formátu a bezchybně extrahovaly doslovné chybové kódy i v situacích se slangem a překlepy.

---

### 5. Závěrečná reflexe

Celé cvičení názorně ukázalo, že vývoj aplikací nad velkými jazykovými modely nelze dělat intuitivním testováním na dvou nebo třech náhodných vstupech, ale vyžaduje exaktní měření číselnými metrikami. Nejvíce mě překvapilo, jak obrovský skok v přesnosti přineslo přidání pouhých tří vhodně zvolených few-shot příkladů – u modelu Qwen na testovací sadě vzrostla úplná shoda z 50 % na 80 %. Fascinující bylo také zjištění, že model střední velikosti (27B) výrazně překonal model s více než 120 miliardami parametrů, a to jak v přesnosti, tak v poloviční latenci. V praktické rovině se ukázala nepostradatelnost lokální diskové mezipaměti (`cache/`), bez níž by ladění evaluačního skriptu neustále naráželo na striktní rate limity bezplatných API. Kdybych projekt dělal znovu, ještě pečlivěji bych formalizoval pravidla pro určení reprodukovatelnosti u fyzických či infrastrukturních incidentů, kde se klasické softwarové pojmy hůře aplikují. Evalační přístup vnímám jako zásadní dovednost pro jakékoliv budoucí profesionální nasazení AI do produkčního prostředí.
