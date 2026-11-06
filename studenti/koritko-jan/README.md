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
| Model | Poskytovatel | Prompt | Sada | Validní JSON | Úplná shoda | město | teplota | srážky | typ srážek | Latence | Tokeny (vstup/výstup) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| openai/gpt-oss-120b | groq | v1 | dev | 100 % | **87 %** | 87 % | 100 % | 100 % | 100 % | 2,21 s | 3 905 / 2 381 |
| openai/gpt-oss-20b | groq | v1 | dev | 100 % | **87 %** | 93 % | 100 % | 93 % | 93 % | 0,93 s | 3 905 / 4 914 |
| openai/gpt-oss-120b | groq | v2 | dev | 100 % | **100 %** | 100 % | 100 % | 100 % | 100 % | 1,66 s | 13 445 / 3 608 |
| openai/gpt-oss-20b | groq | v2 | dev | 100 % | **100 %** | 100 % | 100 % | 100 % | 100 % | 0,68 s | 13 445 / 3 101 |
| openai/gpt-oss-120b | groq | v2 | test | 100 % | **100 %** | 100 % | 100 % | 100 % | 100 % | 2,94 s | 8 980 / 2 447 |
| openai/gpt-oss-20b | groq | v2 | test | 100 % | **100 %** | 100 % | 100 % | 100 % | 100 % | 1,40 s | 8 980 / 2 785 |
<!-- TABULKA KONEC -->

<!-- MODELY START -->
Použité modely: `openai/gpt-oss-120b` (groq, ~120 mld.), `openai/gpt-oss-20b` (groq, ~20 mld. parametrů).
<!-- MODELY KONEC -->

Grafy: [`results/dashboard.html`](results/dashboard.html).
Seznam všech chyb: [`results/chyby.md`](results/chyby.md).

## Rozbor 3 chyb

Tři různé chyby vybírá a popisuje `src/report.py` přímo ze surových odpovědí v `results/` (u každého případu
v sadě je poznamenáno, co je na něm záludné). Všechny chyby jsou v [`results/chyby.md`](results/chyby.md).

<!-- ROZBOR START -->
**1. Případ #8** (openai/gpt-oss-20b, prompt v1, sada dev)

- Vstup: „Plzen: zatazeno, mrholeni, 7 C“
- Model vrátil: `{"mesto": "Plzen", "teplota": 7, "srazky": false, "typ_srazek": null}`
- Správně: `{"mesto": "Plzeň", "teplota": 7, "srazky": true, "typ_srazek": "dest"}`
- Proč: srážky: vrátil false, správně je true; pole typ srážek nechal prázdné, i když údaj v textu je. Na případu je záludné: text bez diakritiky a se zkratkou „C“. Pravidlo je v zadání jasné, jde spíš o **chybu modelu**.

**2. Případ #10** (openai/gpt-oss-120b, prompt v1, sada dev)

- Vstup: „Ahoj, tak jsme dorazili do Zlína a počasí nic moc. Kamarád říkal, že předpověď na dnešek hlásí 12 stupňů, ale fouká jak blázen. Naštěstí aspoň neprší a podle radaru ani nemá.“
- Model vrátil: `{"mesto": "Zlína", "teplota": 12, "srazky": false, "typ_srazek": "zadne"}`
- Správně: `{"mesto": "Zlín", "teplota": 12, "srazky": false, "typ_srazek": "zadne"}`
- Proč: město vrátil jako „Zlína“ místo „Zlín“ – buď jiný pád/tvar, nebo vybral jiné místo. Na případu je záludné: dlouhý hovorový text, údaje jsou rozházené. Pravidlo je v zadání jasné, jde spíš o **chybu modelu**.

**3. Případ #11** (openai/gpt-oss-20b, prompt v1, sada dev)

- Vstup: „Super, v Jihlavě zase „krásné letní počasí“ – leje jako z konve a je 6 stupňů.“
- Model vrátil: `{"mesto": "Jihlavě", "teplota": 6, "srazky": true, "typ_srazek": "dest"}`
- Správně: `{"mesto": "Jihlava", "teplota": 6, "srazky": true, "typ_srazek": "dest"}`
- Proč: město vrátil jako „Jihlavě“ místo „Jihlava“ – buď jiný pád/tvar, nebo vybral jiné místo. Na případu je záludné: ironie – slova „krásné letní počasí“ tvrdí opak skutečnosti. Pravidlo je v zadání jasné, jde spíš o **chybu modelu**.

<!-- ROZBOR KONEC -->

## Doporučení pro 10 000 dotazů denně

Odhad ceny podle cen placených variant na OpenRouteru (ověřeno 6. 11. 2026, kurz 23 Kč/USD) a naměřených tokenů:

<!-- CENA START -->
| Model (OpenRouter) | Prompt | Sada | Ø tokeny vstup / výstup na dotaz | Cena $/1M (vstup/výstup) | 10 000 dotazů USD | ≈ Kč |
|---|---|---|---|---|---|---|
| openai/gpt-oss-120b | v1 | dev | 260 / 159 | 0.026 / 0.095 | 0,218 | 5,0 |
| openai/gpt-oss-20b | v1 | dev | 260 / 328 | 0.018 / 0.09 | 0,342 | 7,9 |
| openai/gpt-oss-120b | v2 | dev | 896 / 241 | 0.026 / 0.095 | 0,462 | 10,6 |
| openai/gpt-oss-20b | v2 | dev | 896 / 207 | 0.018 / 0.09 | 0,347 | 8,0 |
| openai/gpt-oss-120b | v2 | test | 898 / 245 | 0.026 / 0.095 | 0,466 | 10,7 |
| openai/gpt-oss-20b | v2 | test | 898 / 278 | 0.018 / 0.09 | 0,412 | 9,5 |
<!-- CENA KONEC -->

<!-- DOPORUCENI START -->
Vybral bych **openai/gpt-oss-20b** (groq) s promptem **v2**. Na dev sadě má nejvyšší úplnou shodu (100 %, validní JSON 100 %) a na test sadě 100 %, průměrná latence 0,68 s. Při naměřené spotřebě 896 vstupních a 207 výstupních tokenů na dotaz by 10 000 dotazů denně stálo na OpenRouteru asi **0,35 USD (≈ 8 Kč) denně**, tj. ≈ 240 Kč měsíčně. Prompt v2 změnil úplnou shodu v průměru o +13 procentních bodů, ale má 3,4× víc vstupních tokenů – u takhle levných modelů je to pořád zanedbatelná cena, rozhoduje hlavně přesnost.
<!-- DOPORUCENI KONEC -->

## Rozdíl dev a test

<!-- DEVTEST START -->
- openai/gpt-oss-120b + v2: dev 100 % → test 100 % (+0 p. b.)
- openai/gpt-oss-20b + v2: dev 100 % → test 100 % (+0 p. b.)

Test sada má jen 10 případů, takže jeden případ = 10 procentních bodů a rozdíl v řádu desítek bodů může být čistě náhoda. Prompt v2 jsem ladil na dev sadě, proto se na ní dá čekat spíš lepší výsledek než na test (mírné přeučení). Test sada navíc obsahuje typy záludností, které v dev nejsou (°F, text, který není o počasí, krupobití), takže ukazuje, jak nástroj zvládne nové situace.
<!-- DEVTEST KONEC -->

## AI asistent

- Celý projekt (testovací sada, prompty, evaluační skript, report a dashboard i tento README) jsem vytvořil
  s pomocí **Claude (Anthropic)** v aplikaci Claude. Zadal jsem mu úlohu a on připravil celou složku; vyzkoušel
  skript na simulovaném API (cache, chyba 429, nevalidní JSON, validace `summary.json` validátorem dashboardu).
- Pomohl hlavně s rozmyšlením záludných případů a pravidel porovnávání (např. že u rozpětí teplot je potřeba
  předem určit, kterou hodnotu brát) a s ošetřením chyb ve skriptu.
- Kde narazil: z jeho prostředí nešlo volat API Groq/Mistral ani pushovat do forku, eval jsem proto spouštěl
  sám u sebe a výsledky v `results/` pocházejí z mého běhu.
- OpenCode jsem nepoužil (Fáze 0 – asistent), celou práci jsem dělal s Claude.

## Reflexe

Nejvíc mě překvapilo, kolik práce je v testovací sadě a ne v kódu. U zdánlivě jednoduché otázky „jaká je teplota“
se hned ukáže, že je potřeba rozhodnout, co s rozpětím, s °F nebo s textem, kde teplota vůbec není – a dokud to
není napsané v pravidlech, nedá se říct, jestli model odpověděl špatně, nebo jen jinak. Proto je rozdíl mezi
promptem v1 a v2 hlavně v tom, že v2 tyhle konvence modelu prozradí. Dál mě překvapilo, že i malé a levné modely
zvládnou většinu případů a cena za 10 000 dotazů vyjde na korunách až desítkách korun. Příště bych víc času věnoval
vlastnímu procházení chyb a sadu bych udělal větší, protože u 10 testovacích případů jeden případ znamená
10 procentních bodů. Taky bych AI asistenta zkusil použít jen na dílčí úkoly a víc kódu psal sám.
