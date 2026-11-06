# Objednávky v pizzerii



## Co nástroj dělá

Nástroj z krátké české objednávky vytáhne názvy pizz,

počet kusů každé pizzy, doručovací adresu a způsob platby.

Výsledkem je JSON. Chybějící údaje si nevymýšlí.



## Schéma výstupu

- polozky: seznam objektů s poli:

  - nazev: řetězec, název pizzy malými písmeny;

  - pocet: celé kladné číslo nebo null, pokud počet nelze určit.

- adresa: řetězec nebo null.

- platba: "hotovost", "karta" nebo null.



Příklad vstupu:

„Prosím dvě margherity a jednu salámovou na adresu

Pizzová 12, Most. Zaplatím kartou.“



Příklad výstupu:

```json

{

  "polozky": [

    {"nazev": "margherita", "pocet": 2},

    {"nazev": "salamova", "pocet": 1}

  ],

  "adresa": "Pizzová 12, Most",

  "platba": "karta"

}

```



## Pravidla extrakce a porovnávání

- Používám názvy pizz: margherita, salamova, hawai, quattro formaggi.

- České tvary těchto názvů převádím na uvedené názvy.

- Číslovky jako „dvě“ převádím na čísla.

- Chybějící počet, adresu nebo platbu zapisuji jako null.

- Při osobním odběru je adresa null.

- Pokud text neobsahuje žádnou objednanou pizzu, polozky jsou [].

Do polozky patří pouze skutečně objednané pizzy. Pouhá zmínka, dotaz na dostupnost nebo výslovně odmítnutá pizza se nezahrnuje.

- Pořadí položek při porovnávání nerozhoduje.

- U adres ignoruji velikost písmen a nadbytečné mezery;

  diakritiku a ostatní znaky zachovávám.

- Úplná shoda znamená správné položky včetně počtů,

  správnou adresu a správnou platbu.

## Instalace a nastavení

Nainstalujte závislosti pomocí Node.js a npm:

```sh
npm install
```

Vytvořte soubor `.env` podle `.env.example` a doplňte příslušné API klíče.

## Ověření připojení

```sh
node src/smoke.js
node src/smoke-gemini.js
```

Model Gemini lze zadat také výslovně:

```sh
node src/smoke-gemini.js --model models/gemini-3.5-flash
```

Bez parametru skript vybere z dostupných modelů Gemini 3.5 Flash, případně textový Flash-Lite.

### Výsledky ověření

- **Groq** (`openai/gpt-oss-20b`): odpověď „Ahoj“, `prompt_tokens`: 82, `completion_tokens`: 58.
- **Google Gemini** (`models/gemini-3.5-flash`): odpověď „Ahoj“, `prompt_tokens`: 13, `completion_tokens`: 3. Předchozí pokus s `models/gemini-3.8-flash` skončil limitem nebo kvótou.
- **Mistral** blokoval vytvoření klíče na bezplatném plánu, proto nebylo připojení ověřeno.

Při programování jsem zkoušel Gemini a kvůli jeho přetížení přešel na GPT-6.1 Terra přes OpenCode.

## Evaluace

Po instalaci závislostí a nastavení příslušného klíče v `.env` lze spustit evaluaci například takto:

```sh
node src/eval.js --provider groq --model openai/gpt-oss-20b --split dev --prompt v1
node src/eval.js --provider gemini --model models/gemini-3.5-flash --split dev --prompt v1
node src/eval.js --provider openrouter --model google/gemma-4-31b-it:free --split dev --prompt v1
```

Parametr `--split` přijímá `dev` nebo `test`; `--prompt v1` načítá `prompts/v1.txt`. Každá objednávka se odesílá samostatně a správné odpovědi se porovnávají pouze lokálně.

Při použití OpenRouteru skript před měřením zjišťuje zbývající denní free kvótu; při méně než 15 požadavcích nebo nedostupné kvótě měření nespustí. Mezi API voláními OpenRouteru čeká 3,2 sekundy, které se nezapočítávají do latence odpovědi.

Parametr `--cache-only` přepočítá shodu vůči aktuálním referenčním odpovědím pouze z uložených odpovědí, bez síťových volání. Pokud některý záznam chybí, běh skončí bez aktualizace souhrnu.

Podrobné výsledky jednotlivých běhů se ukládají jako JSONL do `results/`, souhrn dokončených běhů do `results/summary.json` a odpovědi pro opakované použití do `cache/`. Pokud se běh přeruší nebo selže, jeho souhrn se neuloží; soubor jednotlivých výsledků může obsahovat jen dokončené případy. Skript při HTTP 429 respektuje `Retry-After` a počet opakování je omezený. API musí vrátit počty vstupních a výstupních tokenů, jinak se běh považuje za neúplný.

### Dosavadní měření

Hodnoty vycházejí z `results/summary.json`; podíly a latence jsou zaokrouhleny.

| Poskytovatel | Model | Prompt | Sada | Případů | Validní JSON | Úplná shoda | Položky | Adresa | Platba | Průměrná latence | Vstupní tokeny | Výstupní tokeny |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Groq | `openai/gpt-oss-20b` | v1 | dev | 15 | 100 % | 93,33 % | 93,33 % | 100 % | 100 % | 0,739 s | 5 774 | 4 844 |
| Groq | `openai/gpt-oss-120b` | v1 | dev | 15 | 100 % | 86,67 % | 93,33 % | 93,33 % | 100 % | 0,889 s | 5 774 | 3 873 |
| OpenRouter | `nvidia/nemotron-3.5-lightning:free` | v1 | dev | 15 | 100 % | 93,33 % | 93,33 % | 100 % | 100 % | 13,838 s | 5 008 | 19 501 |
| Groq | `openai/gpt-oss-20b` | v2 | dev | 15 | 100 % | 93,33 % | 93,33 % | 100 % | 100 % | 0,684 s | 8 699 | 5 142 |
| Groq | `openai/gpt-oss-20b` | v1 | test | 10 | 100 % | 80 % | 80 % | 100 % | 100 % | 1,914 s | 3 842 | 2 818 |
| Groq | `openai/gpt-oss-20b` | v2 | test | 10 | 100 % | 70 % | 80 % | 90 % | 100 % | 0,653 s | 5 792 | 3 029 |

### Srovnání dev a test

Na modelu GPT-OSS 20B dosáhl prompt v1 úplné shody 93,33 % na dev a 80 % na testu; přesnost položek klesla z 93,33 % na 80 %, zatímco adresa a platba zůstaly na 100 %.

Prompt v2 dosáhl úplné shody 93,33 % na dev a 70 % na testu; položky klesly z 93,33 % na 80 %, adresa ze 100 % na 90 % a platba zůstala na 100 %. Validní JSON byl ve všech čtyřech bězích 100 %. Sady mají rozdílnou velikost: dev 15 a test 10 případů.

### Porovnání promptů v1 a v2

#### Výběr před závěrečným měřením

Pro závěrečné měření byly před spuštěním testovací sady vybrány kombinace Groq `openai/gpt-oss-20b` s prompty v1 a v2. Výběr vychází pouze z výsledků na sadě dev: obě kombinace dosáhly úplné shody 93,33 % a stejných shod jednotlivých polí. Prompt v1 přitom použil méně tokenů; v2 má podrobnější instrukce, proto je užitečné porovnat oba na nezávislé sadě. Obsah ani výsledky testovací sady se na výběru nepodílely.

Prompt v2 vznikl ještě před následnou ruční kontrolou referenčních odpovědí. Zpřesňuje povinné schéma, rozdíl mezi JSON hodnotou `null` a řetězcem `"null"`, neurčené počty a adresy, osobní odběr i rozlišení objednaných a pouze zmíněných pizz. Po přepočtu na stejném modelu Groq `openai/gpt-oss-20b` a sadě dev mají oba prompty úplnou shodu 93,33 % a stejné shody jednotlivých polí. Průměrná latence činila 0,739 s u v1 a 0,684 s u v2; vstupní tokeny vzrostly z 5 774 na 8 699 a výstupní z 4 844 na 5 142.

Student následně ručně zkontroloval referenční odpovědi a opravil chybný zápis chybějící adresy. Všechny čtyři dokončené běhy byly poté přepočítány z původních odpovědí v cache proti aktuálním referencím, bez API volání. Dřívější neshody proto nelze automaticky pokládat za chyby modelu.

### Nedokončená měření

Měření Gemini `models/gemini-3.5-flash` na sadě dev nebylo dokončeno: u případu 7 API opakovaně vrátilo HTTP 429. Není proto zahrnuto mezi dokončené běhy v souhrnu.

Měření OpenRouteru `google/gemma-4-31b-it:free` na sadě dev také nebylo dokončeno: u případu 1 API opakovaně vrátilo HTTP 429. Při kontrole před během zbývalo 50 denních free požadavků.

## Fáze 5: Zhodnocení

### Rozbor tří neshod

Následující příklady vycházejí z uložených odpovědí a ručně označených referencí. Pravděpodobné příčiny jsou hypotézy, nikoli zjištěné vnitřní rozhodování modelu.

1. **Chyba výstupu modelu vůči referenci — test ID 20, GPT-OSS 20B, v2.**
   - Vstup: „Dobrý večer, chtěli bychom jednu hawai, jednu margheritu a dvě quattro formaggi. Adresa je Dušičková 73, Pohádkov. Platit budeme kartou.“
   - Odpověď modelu: `{"polozky":[{"nazev":"hawai","pocet":1},{"nazev":"margherita","pocet":1},{"nazev":"quattro formaggi","pocet":2}],"adresa":"Dušičková 73, Pohádkov.","platba":"karta"}`
   - Expected: `{"polozky":[{"nazev":"margherita","pocet":1},{"nazev":"hawai","pocet":1},{"nazev":"quattro formaggi","pocet":2}],"adresa":"Dušičková 73, Pohádkov","platba":"karta"}`
   - Neshoda je v závěrečné tečce adresy; porovnávání ji neignoruje, zatímco pořadí položek nevadí. **Hypotéza:** model převzal do adresy i interpunkci ukončující větu.

2. **Nejasnost interpretace pravidla — test ID 18, GPT-OSS 20B, v1.**
   - Vstup: „Margherita, hotově.“
   - Odpověď modelu: `{"polozky":[{"nazev":"margherita","pocet":null}],"adresa":null,"platba":"hotovost"}`
   - Expected: `{"polozky":[{"nazev":"margherita","pocet":1}],"adresa":null,"platba":"hotovost"}`
   - Referenční odpověď uvádí jeden kus, ale zadání výslovně nestanoví, zda samotný název v jednotném čísle určuje počet; zároveň pro chybějící počet požaduje `null`. **Hypotéza:** model nepředpokládal počet, který nebyl číslovkou uveden. Referenci označil a zkontroloval student; tato neshoda upozorňuje na potřebu upřesnění pravidla.

3. **Opravená chyba reference — dev ID 5, GPT-OSS 20B, v1.**
   - Vstup: „2 quattro formaggi, kartou.“
   - Odpověď modelu: `{"polozky":[{"nazev":"quattro formaggi","pocet":2}],"adresa":null,"platba":"karta"}`
   - Původní expected: `{"polozky":[{"nazev":"quattro formaggi","pocet":2}],"adresa":"null","platba":"karta"}`
   - Původní reference chybně používala řetězec `"null"` místo JSON hodnoty `null`. Student referenci ručně opravil; aktuální expected má `"adresa": null` a odpověď modelu s ním souhlasí. **Hypotéza:** při ručním zadání bylo slovo `null` původně uloženo jako text adresy.

### Doporučení a omezení výsledků

Pro tento projekt doporučuji **GPT-OSS 20B s promptem v1**. Po ruční kontrole referencí dosáhl na dev úplné shody 93,33 % a na testu 80 %, zatímco v2 dosáhl na stejných sadách 93,33 % a 70 %. Oba prompty měly na testu 100 % validních JSON odpovědí. Na testu bylo v2 rychlejší (průměr 0,653 s proti 1,914 s u v1), ale méně přesné a spotřebovalo více tokenů: 5 792 vstupních a 3 029 výstupních proti 3 842 a 2 818 u v1. Na dev byla průměrná latence v1 0,739 s a v2 0,684 s.

Sady jsou malé: dev má 15 a test 10 případů, takže jedna odpověď představuje přibližně 6,67, respektive 10 procentních bodů. Výsledky jsou orientační a rozdíly nejsou důkazem obecného výkonu. Výběr kombinací pro závěrečný test proběhl před jeho spuštěním podle dev výsledků; závěrečný test už nepoužívám k ladění.

### Odhad ceny 10 000 dotazů

Testovací běh GPT-OSS 20B s v1 spotřeboval na 10 dotazů celkem 3 842 vstupních a 2 818 výstupních tokenů. Při stejném průměru by 10 000 dotazů spotřebovalo 3 842 000 vstupních a 2 818 000 výstupních tokenů.

Pro **placený endpoint poskytovatele Groq přes OpenRouter** použiji ceny 0,075 USD za milion vstupních a 0,30 USD za milion výstupních tokenů ([OpenRouter: GPT-OSS 20B](https://openrouter.ai/openai/gpt-oss-20b), ověřeno 6. 11. 2026):

`3,842 × 0,075 + 2,818 × 0,30 = 0,28815 + 0,84540 = 1,13355 USD`

Odhad tedy činí přibližně **1,13355 USD za 10 000 dotazů**. Předpokládá stejné průměrné počty účtovaných tokenů jako v malém testovacím vzorku, jeden požadavek na dotaz a uvedené tokenové sazby bez dalších poplatků či opakovaných požadavků. Jde o modelový přepočet pro uvedený placený endpoint, nikoli skutečně naměřený účet; samotné testovací měření proběhlo přímo přes Groq.

### Použití asistenta a problémy poskytovatelů

Při programování jsem zkoušel Gemini v OpenCode a kvůli jeho přetížení přešel na GPT-6.1 Terra přes OpenCode. Asistent pomáhal s přípravou kódu, evaluačního skriptu, promptů a dokumentace. Správné odpovědi do dat jsem doplňoval a kontroloval ručně pomocí průvodce; později jsem zkontroloval sporné reference a opravil chybný zápis chybějící adresy.

ChatGPT/Codex v chatu jsem používal k vysvětlení zadání, průběžnému vedení a návrhu reflexe, kterou jsem následně upravil.

Mistral blokoval vytvoření klíče na bezplatném plánu. Ověřovací volání Gemini 3.5 Flash odpovědělo, ale měření dev nebylo dokončeno kvůli opakovanému HTTP 429. U OpenRouteru selhalo měření bezplatné Gemmy opakovaným HTTP 429; následné měření bezplatného Nemotronu na dev se dokončilo. Tyto neúspěšné pokusy nejsou započteny jako dokončená měření.

### Vlastní reflexe

Při tomto úkolu jsem zjistil, že nestačí vyzkoušet AI jen na pár příkladech, kde odpoví správně. Nejvíc času mi zabralo nastavení jednotlivých poskytovatelů a řešení problémů s API limity nebo přetížením. Překvapilo mě, že větší model GPT-OSS 120B měl horší výsledky než menší GPT-OSS 20B. Při kontrole dat jsem také narazil na chybu, kdy jsem zaměnil text "null" za skutečnou hodnotu null, což ovlivnilo výsledky. Díky cache jsem ale mohl po opravě dat výsledky znovu přepočítat, aniž bych musel znovu volat API. Taky jsem zjistil, že delší a podrobnější prompt nemusí být vždy lepší. Verze v2 totiž měla na testovacích datech horší výsledky než v1. Rozdělení dat na dev a test mi ukázalo, že je důležité zkoušet prompt i na příkladech, na kterých jsem ho předtím neupravoval. AI mi pomohla hlavně s psaním kódu a opravováním chyb, ale správnost odpovědí jsem si musel kontrolovat sám. Kdybych tento úkol dělal znovu, nejdřív bych si ověřil dostupnost modelů a pořádně zkontroloval data, abych nemusel později opravovat zbytečné chyby.

