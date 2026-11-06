# Evals: změř, jestli AI dělá dobrou práci

**Délka:** 6 hodin, samostatná práce
**Odevzdání:** Pull Request do tohoto repozitáře, nejpozději do konce dnešní praxe (postup viz [Jak odevzdat](#jak-odevzdat))
**Navazuje na:** RAG a embeddingy z minulé hodiny

## Proč tohle děláme

Když postavíš aplikaci s AI, nejčastější chyba je, že ji vyzkoušíš na třech příkladech, řekneš si „vypadá to dobře“ a jedeš dál. Pak změníš prompt nebo model a nevíš, jestli se to zlepšilo, nebo zhoršilo.

Profesionálové to řeší **evaly**: sadou testovacích případů se známou správnou odpovědí, na které se každá změna změří čísly. Je to stejný princip jako unit testy, jen pro AI.

Dnes si postavíš malý AI nástroj, testovací sadu k němu a skript, který změří tři různé modely. Na konci budeš umět s daty v ruce říct, který model a jaký prompt je nejlepší a kolik by to stálo. Přitom si rozjedeš AI asistenta pro programování, který poběží celý den zdarma. Výsledky celé třídy se průběžně sbírají na [společný dashboard](https://doudik.github.io/SPSUL_praxe_5.11/).

**Co se naučíš:**

- kde a jak získat tokeny zdarma a jak s nimi šetřit
- jak připojit AI asistenta pro programování k libovolnému modelu a co zvládnou malé modely
- strukturovaný výstup (LLM vrací JSON, ne volný text)
- jak sestavit testovací sadu a proč ji dělit na vývojovou a testovací část
- metriky: přesnost, validita výstupu, latence, spotřeba tokenů
- porovnání modelů a odhad ceny
- rozbor chyb: proč model selhal a co s tím

## Pravidla

- Jazyk si vyber sám (Python, JS, cokoli). Hodnotí se výsledek, ne jazyk.
- Každý má **jinou úlohu** (viz Fáze 1). Kdo dřív otevře Pull Request s úlohou, ten ji má.
- Pracuješ **jen ve své složce** `studenti/prijmeni-jmeno/`. Na nic jiného v repozitáři nesahej.
- AI asistenta (OpenCode, ChatGPT, cokoli) používat smíš. V README ale napiš, k čemu jsi ho použil. **Správné odpovědi v testovací sadě kontroluješ ty**, ne AI.
- Commituj a pushuj průběžně, aspoň po každé fázi. Jeden commit na konci dne je podezřelý.
- **API klíč nikdy nesmí být v repozitáři.** Ani v historii commitů. Repozitář je veřejný.

---

## Fáze 0: Tokeny zdarma, AI asistent a první volání (45 min)

**Úplně nejdřív** udělej kroky 1 až 3 z [Jak odevzdat](#jak-odevzdat): fork, naklonování a vlastní složka. Ve složce pak budeš celý den pracovat.

### Kde vzít tokeny zdarma

Všichni níže uvedení poskytovatelé mají **API kompatibilní s OpenAI**. Stejný kód tak funguje se všemi, mění se jen adresa (`base_url`), klíč a název modelu.

| Poskytovatel | Registrace | Base URL | Limit zdarma (listopad 2026) | Na co ho dnes použiješ |
|---|---|---|---|---|
| **Mistral** | [console.mistral.ai](https://console.mistral.ai) → plán *Experiment* (zdarma, ověření telefonem) → API Keys | `https://api.mistral.ai/v1` | velkorysý: zhruba 1 požadavek/s a stovky milionů tokenů měsíčně. Přesné limity uvidíš v konzoli v sekci Limits | **hlavní model pro AI asistenta** (Devstral) |
| **Groq** | [console.groq.com](https://console.groq.com) → API Keys | `https://api.groq.com/openai/v1` | okolo **1000 požadavků/den** na model, velmi rychlé, ale jen asi 8 000 tokenů/min | **hlavní práce na evalu** |
| **Google AI Studio** (Gemini) | [aistudio.google.com](https://aistudio.google.com) → Get API key | `https://generativelanguage.googleapis.com/v1beta/openai/` | stovky požadavků/den na modely Flash, přesně na [aistudio.google.com/rate-limit](https://aistudio.google.com/rate-limit) | záloha pro asistenta, třetí model do evalu |
| **OpenRouter** | [openrouter.ai](https://openrouter.ai) → Keys | `https://openrouter.ai/api/v1` | modely s `:free` na konci: 20 požadavků/min, **jen 50 požadavků/den** na celý účet | druhá záloha, bonus s Claude Code |

**Povinně si založ Groq a Mistral, pak Gemini. OpenRouter jen když zbude čas.** Každý má jiné limity a když jeden dojde, přepneš na další. Tohle je běžná praxe i ve firmách.

#### Další bezplatní poskytovatelé (volitelně)

Chceš do evalu pestřejší modely? Tihle dávají API zdarma taky a fungují ve stejném formátu jako OpenAI. Ověřeno 5. 11. 2026:

| Poskytovatel | Registrace | Base URL | Limit zdarma | Zajímavé modely |
|---|---|---|---|---|
| **NVIDIA NIM** | [build.nvidia.com](https://build.nvidia.com) (NVIDIA Developer, ověření telefonem) | `https://integrate.api.nvidia.com/v1` | 40 požadavků/min, 10 000/den | desítky modelů s označením *Free Endpoint*: `z-ai/glm-5.3-flash`, `deepseek-ai/deepseek-v4.1-flash`, `google/gemma-4-31b-it`, `openai/gpt-oss-20b`, `nvidia/nemotron-3-ultra-550b-a55b` |
| **Z.ai** (GLM) | [z.ai](https://z.ai) | `https://api.z.ai/api/paas/v4` | modely *Flash* zdarma | `glm-4.7-flash`, `glm-4.5-flash` |
| **Cohere** (zkušební klíč) | [dashboard.cohere.com](https://dashboard.cohere.com) | `https://api.cohere.ai/compatibility/v1` | asi 1 000 požadavků měsíčně, 20/min | `command-a`, `command-r`, `north-mini-code` |

NVIDIA má ze všech nejštědřejší limity a silné modely na kód, takže se hodí i jako záloha pro AI asistenta (viz níže).

Nabídky se mění každý týden. Aktuální přehled, který se dvakrát týdně automaticky ověřuje, je [awesome-free-ai-coding](https://github.com/mvalentsev/awesome-free-ai-coding). Než ale pošleš data někomu neznámému, podívej se, co s nimi dělá.

**Bezplatné modely na OpenRouteru** najdeš na [openrouter.ai/models](https://openrouter.ai/models) po nastavení filtru ceny na Free. Mají v názvu `:free`, třeba `google/gemma-4-31b-it:free`. Nabídka se často mění. Existuje i `openrouter/free`, který sám vybere nějaký bezplatný model. **Do evalu ho nepoužívej**: pokaždé může odpovídat jiný model, takže výsledky nepůjdou porovnat.

**Na Groqu a Mistralu** najdeš aktuální modely a své limity v konzoli v sekci Limits.

> **Pozor na soukromí:** bezplatné verze mohou tvoje data použít k trénování modelů (u Mistralu s tím při registraci plánu Experiment přímo souhlasíš). Neposílej do nich osobní údaje, hesla ani nic, co nechceš zveřejnit. V testovací sadě používej vymyšlená data.

### AI asistent: OpenCode

[OpenCode](https://opencode.ai) je open-source AI asistent pro programování v terminálu, podobný Claude Code nebo Cursoru. Čte tvůj projekt, píše kód a spouští příkazy. Na rozdíl od nich se jednoduše připojí k **libovolnému poskytovateli**, takže ho rozjedeš zdarma a model přepneš jedním příkazem.

**1. Instalace**

- Windows: `npm install -g opencode-ai` (potřebuješ Node.js), případně `scoop install opencode`
- macOS a Linux: `curl -fsSL https://opencode.ai/install | bash`

**2. Připoj poskytovatele.** Ve své složce spusť `opencode`, napiš `/connect`, vyhledej **Mistral** a vlož klíč. Totéž zopakuj pro **Google** (klíč z AI Studia) a **OpenRouter**. Klíče se uloží do tvé domovské složky, **mimo repozitář**.

**3. Vyber model.** Napiš `/models` a zvol `devstral-latest` od Mistralu. Devstral je model trénovaný přímo na programování a na bezplatném plánu má nejvíc prostoru. Aby se vybral sám při každém spuštění, dej do své složky soubor `opencode.json` (klíč v něm není, commitnout ho můžeš):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "mistral/devstral-latest"
}
```

**4. Ověření.** Zeptej se „Popiš mi, co je v téhle složce.“ Když odpoví, funguje to.

**Když dojde limit nebo to nejde:**

- Chyba 429 (*rate limit*): přepni přes `/models` na jiného poskytovatele. Pořadí: Mistral Devstral → NVIDIA (`glm-5.3-flash` nebo `deepseek-v4.1-flash`, pokud máš účet) → Gemini Flash → bezplatný model na OpenRouteru (s filtrem **Tools**, asistent bez volání nástrojů neumí číst soubory).
- OpenRouter hlásí `No endpoints found matching your data policy`: v [nastavení soukromí na OpenRouteru](https://openrouter.ai/settings/privacy) povol bezplatné modely.
- Na Groqu asistenta nepouštěj. Limit 8 000 tokenů za minutu se vyčerpá jedním dotazem, protože asistent posílá s každým požadavkem velké množství kontextu. Groq si nech na eval.
- Model se zacyklí, nečte soubory nebo píše nesmysly: menší modely to dělají. Zkus jiný. **Zapiš si, co se stalo**, do reflexe se to hodí.

**Jak s asistentem pracovat chytře:**

- Zadávej konkrétní, malé úkoly („napiš funkci, která načte JSONL soubor a vrátí seznam slovníků“), ne „udělej mi celé zadání“. Malé modely na velkých úkolech selhávají.
- Ve své složce si založ krátký `AGENTS.md`: co projekt dělá, v jakém je jazyce, jak se spouští. OpenCode ho čte automaticky a nemusí pokaždé procházet všechny soubory. (Příkaz `/init` ho vygeneruje sám.)
- Kód, který asistent napíše, si přečti. Za odevzdaný kód ručíš ty.

### Klíče do vlastního kódu

1. Klíče pro eval dej do souboru `.env` ve své složce (`GROQ_API_KEY=...`, `GEMINI_API_KEY=...`, `MISTRAL_API_KEY=...`, `OPENROUTER_API_KEY=...`).
2. Přidej `.env.example` se stejnými názvy proměnných, ale bez hodnot.
3. `.env` je v kořenovém `.gitignore`, takže ho git nepřidá. **Než poprvé commitneš**, stejně spusť `git status` a zkontroluj, že tam `.env` není.

Když klíč omylem commitneš a pushneš, nestačí ho smazat dalším commitem, protože v historii zůstane. Musíš ho **u poskytovatele zneplatnit a vygenerovat nový**. Roboti procházejí GitHub a uniklé klíče najdou během minut.

### První volání

Ověř, že ti klíč na Groqu funguje:

```bash
curl https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer $GROQ_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "openai/gpt-oss-20b", "messages": [{"role": "user", "content": "Ahoj, odpověz jedním slovem."}]}'
```

V odpovědi najdi pole `usage`. Uvidíš v něm `prompt_tokens` a `completion_tokens`, tedy kolik tokenů šlo do modelu a kolik z něj přišlo. Tahle čísla budeš sbírat.

Na Windows spouštěj `curl` v Git Bash (v PowerShellu má jinou syntaxi), nebo rovnou napiš krátký skript.

V Pythonu i JS můžeš použít oficiální knihovnu `openai`. Stačí jí nastavit `base_url` a `api_key` podle tabulky výše.

### Kolik toho dnes spotřebuješ

| Co | Kde | Zhruba požadavků |
|---|---|---|
| AI asistent během dne | Mistral, záloha NVIDIA, Gemini a OpenRouter | desítky až stovky |
| ladění evalu na 2 až 3 případech | Groq | 20 |
| celý eval (Fáze 4) | Groq, Gemini nebo Mistral | 80 |

Eval ukládá odpovědi do mezipaměti (Fáze 3), takže opakované spuštění nic nestojí.

✅ **Kontrolní bod:** OpenCode odpovídá přes Mistral, máš funkční volání aspoň u dvou poskytovatelů a `.env` není v gitu.

---

## Fáze 1: Vyber úlohu a otevři Pull Request (30 min)

Postavíš nástroj, který z krátkého českého textu **vytáhne strukturované údaje do JSONu**. Úloha musí mít jednoznačně správnou odpověď, kterou dokážeš sám ověřit, jinak ji nepůjde měřit.

**Náměty** (můžeš mít i vlastní, ale každý jiný):

1. E-maily na školní helpdesk: kategorie, priorita, oddělení
2. Recenze z e-shopu: sentiment, hodnocený aspekt (cena, doprava, kvalita)
3. Inzeráty bytů: cena, dispozice, plocha v m², město
4. Inzeráty aut: značka, model, rok, nájezd v km, cena
5. Pracovní nabídky: pozice, mzda od a do, home office ano/ne, technologie
6. Hlášení závad v učebně: zařízení, učebna, závažnost
7. Účtenky přepsané do textu: obchod, datum, celková částka
8. Bug reporty: komponenta, závažnost, je reprodukovatelný ano/ne
9. Sportovní zprávy: týmy, skóre, vítěz
10. SMS zprávy: phishing ano/ne, typ podvodu
11. Komentáře na fóru: toxický ano/ne, typ (urážka, spam, v pořádku)
12. Pozvánky na akce: název, datum, čas, místo
13. Dotazy z IT fóra: komponenta, problém, operační systém
14. Jídelníček: název jídla, alergeny (čísla)
15. Dopravní hlášení: linka, zpoždění v minutách, příčina
16. Objednávky v pizzerii: položky, počet kusů, adresa, platba
17. Zprávy o počasí: město, teplota, srážky ano/ne
18. Studijní dotazy: předmět, typ dotazu (termín, známka, omluvenka)

**Než si úlohu vybereš**, projdi [otevřené Pull Requesty](https://github.com/doudik/SPSUL_praxe_5.11/pulls). Úloha, která už v názvu nějakého PR je, je zabraná.

**Hned jak si úlohu vybereš**, otevři Pull Request jako *Draft* (postup viz [Jak odevzdat](#jak-odevzdat)). Název PR: `Příjmení Jméno: úloha`, například `Novák Jan: inzeráty aut`. Tím si úlohu zamluvíš.

Do `README.md` ve své složce pak popiš:

- **co nástroj dělá** (2 až 3 věty),
- **přesné schéma výstupu**: názvy polí, jejich typ a u kategorií povolené hodnoty. Například:

```json
{
  "typ": "urazka | spam | v poradku",
  "skore_toxicity": "1 | 2 | 3 | 4 | 5",
  "akce" : "schvalit | smazat | vyzaduje_kontrolu"
}
```

- **pravidla porovnávání**: kdy považuješ odpověď za správnou (malá a velká písmena, mezery, „1 500 Kč“ proti 1500 a podobně).

Doporučuji 3 až 5 polí. Kombinace kategorie a extrahovaného údaje dává nejzajímavější výsledky.

✅ **Kontrolní bod:** Draft PR je otevřený, README ve tvé složce obsahuje popis úlohy, schéma a pravidla porovnávání. Commitni a pushni.

---

## Fáze 2: Testovací sada (60 min)

Tohle je nejdůležitější část celé práce. Špatná testovací sada znamená bezcenná čísla.

Vytvoř **25 testovacích případů**. Každý obsahuje vstupní text a správnou odpověď (tzv. *gold*):

```json
{"id": 1, "input": "Dobrý den, v učebně 204 nejde zapnout projektor, za hodinu tam máme maturitní prezentace.", "expected": {"kategorie": "hardware", "priorita": "vysoka", "ucebna": "204"}}
```

Formát: JSONL (jeden JSON objekt na řádek) nebo CSV.

**Požadavky:**

- Aspoň **5 záludných případů**: chybějící údaj (správně je `null`), dva údaje v jednom textu, překlep, ironie, údaj v jiném formátu („patnáct set“), text, který do žádné kategorie nepatří.
- Záludné případy označ (`"tezky": true`).
- Případy se mezi sebou mají lišit délkou, stylem i tématem. 25 skoro stejných vět nic nezměří.

**Rozděl sadu na dvě části:**

- `data/dev.jsonl`: 15 případů. Na nich ladíš prompt.
- `data/test.jsonl`: 10 případů. Ty **nikdy nepoužiješ k ladění**. Spustíš je až na konci a výsledek reportuješ.

> **Proč dělit?** Když ladíš prompt na stejných datech, na kterých pak měříš, prompt se „naučí“ přesně tyhle případy a čísla vyjdou lepší, než jaká budou ve skutečnosti. Říká se tomu přeučení (*overfitting*) a v AI je to jedna z nejčastějších chyb. Je to stejné, jako kdybys znal otázky z písemky předem.

Vstupní texty ti může pomoct vymyslet AI. **Správné odpovědi ale vyplň a zkontroluj sám.** Každý případ si přečti a rozhodni, co je správně.

✅ **Kontrolní bod:** 15 + 10 případů, aspoň 5 záludných, správné odpovědi zkontrolované. Commitni a pushni.

---

## Fáze 3: Evaluační skript (75 min)

Napiš program, který:

1. Načte sadu (`dev` nebo `test`) a prompt ze souboru (`prompts/v1.txt`).
2. Každý případ pošle modelu. Nastav **`temperature: 0`**, aby výsledky šly opakovat.
3. Odpověď zkusí rozparsovat jako JSON. Když to nejde, započítá případ jako **nevalidní výstup**. Nepadá na tom celý program.
4. Porovná výstup se správnou odpovědí podle tvých pravidel z Fáze 1.
5. U každého volání si uloží `prompt_tokens`, `completion_tokens` a dobu odpovědi.
6. Vypíše a uloží do `results/` souhrn:
   - **validní JSON** v % případů
   - **přesnost po polích** (u kolika % případů sedí `kategorie`, `priorita`...)
   - **úplná shoda** (% případů, kde sedí všechna pole)
   - **průměrná latence** v sekundách
   - **tokeny celkem** (vstup a výstup zvlášť)
7. Uloží i surové odpovědi modelu, aby šly zpětně zkontrolovat.
8. Každý běh přidá do souboru **`results/summary.json`** ve **přesně tomhle formátu**. Z něj se plní [společný dashboard třídy](https://doudik.github.io/SPSUL_praxe_5.11/), takže názvy klíčů neměň:

```json
{
  "student": "Jan Novák",
  "uloha": "Inzeráty aut",
  "behy": [
    {
      "model": "openai/gpt-oss-20b",
      "poskytovatel": "groq",
      "prompt": "v1",
      "sada": "dev",
      "pripadu": 15,
      "validni_json": 1.0,
      "uplna_shoda": 0.6,
      "pole": {"znacka": 0.93, "rok": 0.87, "cena": 0.8},
      "latence_s": 0.42,
      "tokeny_vstup": 3100,
      "tokeny_vystup": 900
    }
  ]
}
```

- `sada` je `"dev"` nebo `"test"`, `prompt` je `"v1"` nebo `"v2"`.
- Podíly (`validni_json`, `uplna_shoda`, hodnoty v `pole`) jsou **čísla od 0 do 1**, ne procenta. 60 % je `0.6`.
- `latence_s` je průměr v sekundách, `tokeny_vstup` a `tokeny_vystup` jsou součty za celý běh.
- Stejný běh spuštěný znovu ať záznam přepíše, ne přidá další.

**Mezipaměť (povinné):** než pošleš požadavek, spočítej klíč z kombinace model + prompt + vstup (třeba jejich hash) a podívej se do složky `cache/`. Když tam odpověď je, použij ji a API nevolej. Ušetříš limity a skript pak můžeš spouštět kolikrát chceš. Složka `cache/` je v `.gitignore`.

Model a poskytovatel ať se nastavují parametrem nebo konfigurací, ne přepisováním kódu.

**Chyba 429 je normální.** Bezplatné úrovně mají limit požadavků i tokenů za minutu (Groq asi 8 000 tokenů/min, takže ho celá sada rychle vyčerpá). Skript proto musí při chybě 429 počkat (třeba 10 až 20 sekund) a zkusit to znovu, ne spadnout. Případně mezi požadavky dej krátkou pauzu.

**Tip pro JSON výstup:** někteří poskytovatelé podporují `"response_format": {"type": "json_object"}`. Ne každý free model ho ale zvládá. V promptu proto vždy výslovně napiš, ať model vrátí jen JSON. Validita výstupu je jedna z věcí, které měříš.

✅ **Kontrolní bod:** skript proběhne na `dev` sadě s jedním modelem a vypíše metriky. Druhé spuštění nespotřebuje žádné požadavky. Commitni a pushni. Obvykle do 15 minut se tvůj výsledek objeví na [dashboardu třídy](https://doudik.github.io/SPSUL_praxe_5.11/). Když u tebe svítí červená chyba, oprav formát `summary.json`.

---

## Fáze 4: Experimenty (60 min)

### 4a: Porovnání modelů

S promptem `v1` pusť `dev` sadu na **3 různých modelech**, ideálně od aspoň 2 poskytovatelů (například 2 modely na Groqu a 1 na Gemini, nebo cokoli z tabulky dalších poskytovatelů ve Fázi 0). Vyber modely různé velikosti, ať je co porovnávat: třeba jeden malý kolem 8 až 20 miliard parametrů a jeden velký nad 70 miliard.

> Když ti nějaká registrace nepůjde, stačí 3 modely od jednoho poskytovatele. Napiš to do README.

### 4b: Lepší prompt

Projdi chyby z 4a a napiš `prompts/v2.txt`. Vyzkoušej aspoň jednu z technik:

- **few-shot**: dej do promptu 2 až 3 vyřešené příklady (**ne** z testovací sady!)
- přesnější popis kategorií, včetně toho, kdy kterou nepoužít
- výslovná instrukce pro chybějící údaje (`null`)
- schéma JSONu přímo v promptu

Pusť `v2` na `dev` sadě aspoň na jednom modelu a porovnej s `v1`.

### 4c: Finální měření

Vyber nejlepší kombinaci model + prompt a **teprve teď** ji pusť na `test` sadě. Pusť tam pro srovnání i druhou nejlepší kombinaci.

**Výsledky dej do tabulky v README**, například:

| Model | Poskytovatel | Prompt | Sada | Validní JSON | Úplná shoda | Pole „kategorie“ | Latence | Tokeny (vstup/výstup) |
|---|---|---|---|---|---|---|---|---|
| ... | Groq | v1 | dev | 100 % | 60 % | 87 % | 0,4 s | 3 100 / 900 |

✅ **Kontrolní bod:** tabulka v README, soubory s výsledky v `results/`, všechny běhy v `summary.json`. Commitni a pushni a na [dashboardu třídy](https://doudik.github.io/SPSUL_praxe_5.11/) porovnej své výsledky s ostatními. Vyhrává u všech stejný model?

---

## Fáze 5: Rozbor a závěr (45 min)

Do README ve své složce dopiš:

1. **Rozbor 3 chyb.** U každé: vstup, co model vrátil, co je správně a **proč si myslíš, že se spletl**. Šlo o nejasné zadání, chybu modelu, nebo chybu v tvé správné odpovědi? I to se stává a přiznat to je v pořádku.
2. **Doporučení.** Kdybys tenhle nástroj nasazoval na 10 000 dotazů denně, jaký model a prompt bys vybral a proč? Zohledni přesnost, rychlost i cenu. U zvoleného modelu najdi na OpenRouteru cenu placené (ne `:free`) varianty a z naměřených tokenů spočítej, **kolik by stálo 10 000 dotazů**.
3. **Rozdíl dev a test.** Liší se výsledky? Proč?
4. **AI asistent.** Jaké modely jsi v OpenCode použil, kdy a proč jsi přepínal, s čím ti pomohl a kde selhal. Poznal jsi rozdíl mezi menším a větším modelem?
5. **Reflexe (5 až 10 vět).** Co tě překvapilo? Co bys udělal jinak?

---

## Bonusy (max. +10 bodů, až máš hotové všechno ostatní)

- **Konzistence (+3):** pusť 5 případů 5krát s `temperature: 1`. Jak moc se odpovědi liší?
- **LLM jako hodnotitel (+4):** přidej do schématu pole s volným textem (třeba `shrnuti`). Nech jiný model ohodnotit shrnutí na škále 1 až 5 a na 10 případech porovnej jeho hodnocení se svým. Shodnete se?
- **Embeddingy (+3):** volný text porovnej se správnou odpovědí přes kosinovou podobnost embeddingů z minulé hodiny místo přesné shody. Kdy to dává lepší výsledky?
- **Vlastní dashboard (+3):** skript vyrobí z `results/summary.json` HTML stránku `results/dashboard.html` s grafy: porovnání modelů, v1 proti v2, dev proti test a přesnost po jednotlivých polích. Stačí čisté HTML a JS bez frameworku. Dashboard třídy ti může posloužit jako inspirace.
- **Claude Code přes OpenRouter (+3):** rozjeď [Claude Code](https://claude.com/claude-code) s bezplatným modelem a zadej mu stejný malý úkol jako OpenCode. V README porovnej výsledek a spotřebu požadavků. Postup:
  1. Instalace: Windows `irm https://claude.ai/install.ps1 | iex`, macOS a Linux `curl -fsSL https://claude.ai/install.sh | bash`.
  2. Do `~/.claude/settings.json` (na Windows `C:\Users\<tvoje jméno>\.claude\settings.json`, mimo repozitář) vlož níže uvedený blok. Model vyber na OpenRouteru s filtry **Free** a **Tools** a nastav ho do všech čtyř řádků, jinak Claude Code na pozadí volá placený model. `ANTHROPIC_API_KEY` musí zůstat prázdný řetězec.
  3. Spusť `claude`, napiš `/status` a zkontroluj, že je tam `https://openrouter.ai/api`. Spotřebu sleduj na [openrouter.ai/activity](https://openrouter.ai/activity).

  ```json
  {
    "env": {
      "ANTHROPIC_BASE_URL": "https://openrouter.ai/api",
      "ANTHROPIC_AUTH_TOKEN": "sk-or-v1-TVUJ-KLIC",
      "ANTHROPIC_API_KEY": "",
      "ANTHROPIC_DEFAULT_OPUS_MODEL": "cohere/north-mini-code:free",
      "ANTHROPIC_DEFAULT_SONNET_MODEL": "cohere/north-mini-code:free",
      "ANTHROPIC_DEFAULT_HAIKU_MODEL": "cohere/north-mini-code:free",
      "CLAUDE_CODE_SUBAGENT_MODEL": "cohere/north-mini-code:free"
    }
  }
  ```

  Pozor: OpenRouter dává zdarma jen 50 požadavků denně a jeden větší úkol v Claude Code jich spotřebuje 10 až 30.

  Alternativa: [FreeInference](https://freeinference.org) (výzkumná služba Harvardu) má zdarma endpoint ve formátu Anthropic, takže Claude Code jde napojit přímo. Stačí `ANTHROPIC_BASE_URL` nastavit na `https://freeinference.org/anthropic` a klíč z jejich webu. Limity nezveřejňují a prompty si můžou ukládat pro výzkum.

---

## Když nestíháš

- **Fáze 0 ti trvá přes hodinu** (registrace nejde, instalace neprojde): nech asistenta být, pokračuj Fází 1 a v README napiš, co nefungovalo. Bez asistenta přijdeš nejvýš o 5 bodů.
- **Hodinu před koncem nemáš Fázi 4:** změř, co máš (i jen jeden model), a napiš Fázi 5. Rozbor chyb a reflexe dávají víc bodů než třetí model.
- Odevzdej vždycky. Rozpracovaný Pull Request se hodnotí, chybějící ne.

## Jak odevzdat

1. Vpravo nahoře na této stránce klikni na **Fork** a vytvoř si vlastní kopii repozitáře.
2. Svůj fork si naklonuj (`git clone https://github.com/<tvuj-ucet>/SPSUL_praxe_5.11.git`).
3. Vytvoř složku `studenti/prijmeni-jmeno/` (jen malá písmena bez diakritiky, číslice a pomlčky, například `studenti/novak-jan/`, jinak tě dashboard nenajde) a v ní soubor `README.md` s názvem úlohy. Commitni a pushni do svého forku.
4. Na GitHubu ve svém forku klikni na **Contribute → Open pull request**. Rozbal šipku u tlačítka **Create pull request** a zvol **Create draft pull request**. Název: `Příjmení Jméno: úloha`.
5. Pracuj a pushuj průběžně do svého forku. Pull Request se aktualizuje sám.
6. Až budeš hotový, klikni v Pull Requestu na **Ready for review**. Tím odevzdáváš. Udělej to nejpozději do konce dnešní praxe.

**Struktura tvé složky** (názvy souborů v `src/` jsou na tobě):

```
studenti/prijmeni-jmeno/
  README.md          popis úlohy, schéma, jak spustit, tabulka výsledků, rozbor, reflexe
  AGENTS.md          krátký kontext pro AI asistenta
  opencode.json      výchozí model pro OpenCode
  .env.example       názvy proměnných bez hodnot
  data/dev.jsonl
  data/test.jsonl
  prompts/v1.txt
  prompts/v2.txt
  src/...            tvůj kód
  results/summary.json  souhrn všech běhů pro dashboard (přesný formát viz Fáze 3)
  results/...        surové odpovědi
```

Do README napiš i **jak projekt spustit** (instalace, příkaz).

## Hodnocení

| Část | Body |
|---|---|
| Fáze 0: OpenCode s bezplatným modelem, `AGENTS.md`, klíče mimo git, `.env.example`, návod ke spuštění | 15 |
| Fáze 1: včas otevřený Draft PR, popis úlohy, schéma, pravidla porovnávání | 10 |
| Fáze 2: 25 případů, 5 záludných, rozdělení dev/test, správné odpovědi sedí | 20 |
| Fáze 3: skript funguje, všechny metriky, mezipaměť, odolnost vůči nevalidnímu JSONu, `summary.json` ve správném formátu | 25 |
| Fáze 4: 3 modely, prompt v2, finální měření na test sadě, tabulka | 15 |
| Fáze 5: rozbor chyb, doporučení s výpočtem ceny, zkušenost s AI asistentem, reflexe | 15 |
| **Celkem** | **100** |
| Bonusy | +10 |

**Srážky:**

- API klíč v repozitáři nebo v historii commitů: **−20 bodů**
- ladění promptu na test sadě (příklady z test sady ve few-shot): **−10 bodů**
- čísla v README neodpovídají souborům v `results/`: **−10 bodů**
- změny mimo vlastní složku: **−5 bodů**

**Převod na známku:** 90+ bodů = 1, 75+ = 2, 60+ = 3, 45+ = 4, méně = 5.

## Rozbory a Hodnocení Evaluace

### 1. Rozbor 3 chyb z evaluace

#### Chyba 1: Detekce ironie a sarkasmu (ID 14 v dev sadě)
* **Vstup:** `"Dneska na to koukám a říkám si: 'Kterej kretén tohle psal?' No a pak kouknu na git blame a tam moje jméno z minulýho roku..."`
* **Co model vrátil:** `{"typ": "urazka", "skore_toxicity": "3", "akce": "vyzaduje_kontrolu"}`
* **Co je správně (expected):** `{"typ": "v poradku", "skore_toxicity": "1", "akce": "schvalit"}`
* **Proč se spletl:** Jedná se o chybu modelu v chápaní kontextu a sebeironie. Model zachytil vulgární slovo („kretén“) a automaticky ho vyhodnotil jako útok na jiného uživatele. Nedokázal rozpoznat, že autor píše s nadsázkou o svém vlastním starém kódu.

#### Chyba 2: Hraniční vulgarita vs. vyžadování kontroly (ID 3 v test sadě)
* **Vstup:** `"Co to je za kecy? Ty musíš mít v hlavě fakt vymatláno, když tvrdíš takovou kravinu."`
* **Co model vrátil:** `{"typ": "urazka", "skore_toxicity": "2", "akce": "schvalit"}`
* **Co je správně (expected):** `{"typ": "urazka", "skore_toxicity": "3", "akce": "vyzaduje_kontrolu"}`
* **Proč se spletl:** Jde o nejasnou hranici v zadání a nastavení promptu. Model sice správně určil typ jako `urazka`, ale podcenil skóre toxicity (dal 2 místo 3) a zvolil akci `schvalit`. Menší modely mají tendenci podceňovat méně agresivní urážky, pokud neobsahují explicitní sprostá slova nejhrubšího kalibru.

#### Chyba 3: Falešný poplach u technického výrazu (ID 6 v dev sadě)
* **Vstup:** `"Tento update stojí úplně za nic. Vývojáři jsou líná stvoření a jen z lidí tahají peníze."`
* **Co model vrátil:** `{"typ": "urazka", "skore_toxicity": "3", "akce": "vyzaduje_kontrolu"}`
* **Co je správně (expected):** `{"typ": "v poradku", "skore_toxicity": "2", "akce": "schvalit"}`
* **Proč se spletl:** Chyba v naší definici v `expected` vs. striktnost modelu. Výrok vyjadřuje silnou frustraci ze softwaru a kritizuje vývojáře. Z lidského pohledu jde o běžný názor na fóru (proto `v poradku`), ale model kritiku vyhodnotil jako osobní útok. Zde byla hranice mezi objektivní kritikou a urážkou nastavená hodně těsně.

---

### 2. Doporučení pro produkční nasazení (10 000 dotazů / den)

Na základě naměřených dat jednoznačně doporučuji pro produkční nasazení vybrat model **`openai/gpt-oss-20b`** (poskytovatel Groq) v kombinaci s **Promptem v1**.

* **Důvody pro výběr z naměřených výsledků:**
  * **Přesnost:** Jako jediný dosáhl **100% validního JSONu** (1.0) a nejvyšší úplné shody (**60 %**). V jednotlivých polích dosáhl excelentní shody u pole `typ` (100 %) a `akce` (90 %).
  * **Rychlost (Latence):** S průměrnou latencí **0.46 s** je více než 10× rychlejší než modely Gemini (které trvaly přes 5 sekund).

#### Přesný výpočet nákladů na 10 000 dotazů denně:
* **Z naměřených dat pro 10 případů:**
  * Vstupní tokeny celkem: 5 740 $\rightarrow$ **574 tokenů na 1 dotaz**
  * Výstupní tokeny celkem: 2 023 $\rightarrow$ **202 tokenů na 1 dotaz**
* **Spotřeba pro 10 000 dotazů:**
  * Vstup: $10\,000 \times 574 = 5\,740\,000\text{ tokenů}$ ($5.74\text{M}$)
  * Výstup: $10\,000 \times 202 = 2\,020\,000\text{ tokenů}$ ($2.02\text{M}$)
* **Cena na OpenRouteru pro `openai/gpt-oss-20b` (placená variant):**
  * Input: \$0.05 za 1M tokenů
  * Output: \$0.10 za 1M tokenů
* **Výpočet ceny za den:**
  $$\text{Input cena} = 5.74 \times 0.05 = \$0.287$$
  $$\text{Output cena} = 2.02 \times 0.10 = \$0.202$$
  $$\mathbf{\text{Celková denní cena}} = \mathbf{\$0.489\text{ USD}}\text{ (cca 11.50 Kč / den)}$$
* **Měsíční náklady (30 dní):** cca **\$14.67 USD** (cca 345 Kč za měsíc za zpracování 300 000 dotazů).

---

### 3. Rozdíl mezi sadami `dev` a `test`

Výsledky na sadě `test` ukázaly reálné limity jednotlivých modelů. Zatímco `openai/gpt-oss-20b` si udržel vysokou přesnost, ostatní modely na testovací sadě výrazně propadly (shoda pouze 20–30 %).
* **Proč se výsledky liší:**
  1. **Overfitting na dev sadu:** System prompt byl původně laděn a testován na pravidlech z `dev` sady. `test` sada prověřila, jak dobře dokážou modely pravidla zobecnit.
  2. **Těžší případy v test sadě:** Sada `test` obsahuje více zákeřných příkladů, sarkasmu a nejednoznačných formulací.
  3. **Dodržení JSON formátu:** Zatímco `openai/gpt-oss-20b` neměl s formátem problém (1.0), Gemini na sadě `test` generoval neplatný JSON v 30–40 % případů.

---

### 4. Využití AI asistenta (OpenCode / Gemini)

Během vypracování projektu jsem používval AI asistenta v OpenCode.

* **Použité modely:**
  * Na návrh architektury skriptu `eval.js`, kešování přes SHA-256 a správu CLI argumentů jsem používal větší modely.
  * Na řešení syntaxe PowerShellu, úpravu `loadDataset` a funkce `normalize` jsem používal menší/rychlejší modely.
* **S čím AI pomohla:**
  * Vytvoření kompletní infrastruktury `eval.js` a vyřešení parsování dat (podpora `.json` i `.jsonl`).
  * Návrh normalizační logiky pro porovnávání výsledků bez ohledu na diakritiku a velikost písmen.
  * Výpočet a formátování statistik v `summary.json`.
* **Kde AI selhala:**
  * AI zpočátku navrhovala neexistující nebo zastaralá ID modelů pro Groq/Mistral API, což vracelo chyby 404.
  * Příkazová řádka PowerShellu se rozbíjela u názvů modelů s mezerami (např. chybějící uvozovky u `openai/gpt-oss-20b`).
* **Rozdíl mezi menším a větším modelem:**
  * Menší modely psaly kód rychle, ale často přehlédly edge-cases (např. typové konverze string vs. number). Větší modely hned napoprvé navrhly spolehlivé struktury.

---

### 5. Osobně-technická reflexe

Překvapilo mě, jak propastné rozdíly v latenci a spolehlivosti JSON výstupu existují mezi jednotlivými poskytovateli. Model `openai/gpt-oss-20b` na Groqu dokázal vrátit validní odpověď za necelou půlsekundu, zatímco modely Gemini potřebovaly přes 5 sekund a navíc často selhávaly na syntaxi JSONu. 

Kdybych dělal projekt znovu, zaměřil bych se od začátku na striktní ošetření diakritiky v porovnávací logice a rovnou definoval uvozovky u CLI argumentů v PowerShellu. Ukázalo se, že výběr správného poskytovatele a optimalizace infrastruktury (kešování, normalizace) má na celkový výkon systému stejně velký vliv jako samotná volba modelu.
