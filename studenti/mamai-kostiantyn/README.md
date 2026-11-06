# SMS zprávy: phishing a typ podvodu

## Co nástroj dělá

Nástroj z krátké české SMS zprávy určí, zda jde o phishingové nebo jiné podvodné
sdělení. Pokud je zpráva podvodná, přiřadí jí jeden typ podvodu podle obsahu.

## Schéma výstupu

```json
{
  "phishing": true,
  "typ_podvodu": "banka | doruceni | urady | investice | vyhra | ucet | jine | null"
}
```

- `phishing` (`boolean`) — `true`, pokud se zpráva snaží příjemce podvést,
  vylákat přihlašovací údaje, peníze nebo jiné citlivé údaje; jinak `false`.
- `typ_podvodu` (`string nebo null`) — typ podvodu, pokud je zpráva phishingová;
  pro běžnou legitimní zprávu je `null`.

Povolené hodnoty `typ_podvodu`:

- `banka` — zpráva se vydává za banku nebo platební službu;
- `doruceni` — falešné doručení balíku nebo doplatku za dopravu;
- `urady` — vydává se za úřad, policii nebo jinou veřejnou instituci;
- `investice` — slibuje snadný zisk nebo láká na investování;
- `vyhra` — falešná výhra, soutěž nebo odměna;
- `ucet` — krádež přístupu k účtu mimo bankovní zprávy, například k e-mailu;
- `jine` — podvod, který nespadá do žádné z uvedených kategorií.

## Pravidla porovnávání

- Porovnávání JSON hodnot je přesné podle názvů polí a jejich hodnot.
- U textových hodnot ignoruji velikost písmen, nadbytečné mezery a rozdíly mezi
  českou diakritikou a její verzí bez diakritiky.
- `phishing` musí být skutečná logická hodnota `true` nebo `false`, ne text.
- U legitimní zprávy musí být `typ_podvodu` přesně `null`.
- U podvodné zprávy musí `typ_podvodu` obsahovat jednu z povolených hodnot.
- Pokud zpráva obsahuje více podvodných motivů, rozhoduje hlavní účel zprávy;
  pokud jej nelze určit, použije se `jine`.

## Stav práce

Úloha: klasifikace SMS zpráv podle toho, zda jde o phishing, a podle typu
podvodu. Testovací data, prompty, evaluační skript a výsledky jsou uloženy
v této složce.

## Spuštění evaluace

Vytvoř soubor `.env` podle `.env.example` a doplň API klíče. Soubor `.env` se
nesmí commitnout do repozitáře.

Z kořene této složky spusť například:

```bash
python src/eval.py --provider openrouter --model cohere/north-mini-code:free --set dev --prompt v1
python src/eval.py --provider openrouter --model nvidia/nemotron-3.5-lightning:free --set dev --prompt v1
python src/eval.py --provider openrouter --model liquid/lfm-2.5-2.6b:free --set dev --prompt v1
```

Provider, model, sada a prompt se nastavují parametry příkazového řádku.
Odpovědi se ukládají do `cache/`, podrobné výsledky do `results/`, a souhrn
všech běhů do `results/summary.json`.

## Výsledky experimentů

Všechny dokončené běhy byly provedeny na sadě `dev` s promptem `v1`.

| Model | Poskytovatel | Validní JSON | Úplná shoda | Pole `phishing` | Pole `typ_podvodu` | Latence | Tokeny vstup/výstup |
|---|---|---:|---:|---:|---:|---:|---:|
| `cohere/north-mini-code:free` | OpenRouter | 100 % | 93,33 % | 93,33 % | 93,33 % | 1,90 s | 5 570 / 2 115 |
| `nvidia/nemotron-3.5-lightning:free` | OpenRouter | 100 % | 93,33 % | 93,33 % | 93,33 % | 9,68 s | 7 302 / 11 001 |
| `liquid/lfm-2.5-2.6b:free` | OpenRouter | 86,67 % | 73,33 % | 86,67 % | 73,33 % | 2,40 s | 6 717 / 12 250 |

Výsledek Liquid je pouze částečný: dva případy skončily chybou `429` kvůli
limitu upstream poskytovatele. Proto jeho metriky zahrnují i tyto dva
nevalidní pokusy a nejsou přímo srovnatelné s kompletními běhy.

## Omezení experimentu

Gemini nebylo možné změřit, protože model `gemini-2.5-flash` byl pro nové
uživatele nedostupný. Groq vracel HTTP 403 ještě před odpovědí modelu. OpenRouter
později vyčerpal denní limit 50 požadavků, takže finální měření na sadě `test`
nebylo možné dokončit před deadlinem. Neúspěšné požadavky nejsou uvedené jako
platné výsledky v `results/summary.json`.

## Rozbor chyb

1. **Dev, případ 9, Cohere:** SMS nabízela „zhodnocení úspor“ a žádala odpověď
   `ANO`. Model vrátil `phishing: false` a `typ_podvodu: null`, přestože šlo o
   investiční podvod. Pravděpodobně podlehl neutrálnímu tónu a absenci odkazu.
   Ve v2 promptu je proto výslovně uvedeno, že podvod může probíhat i bez odkazu
   a že žádost o odpověď může být podvodným požadavkem.
2. **Dev, případ 9, Nemotron:** Model udělal stejnou chybu a legitimní zprávu
   nerozpoznal jako investiční podvod. To ukazuje, že právě nejednoznačné
   investiční nabídky jsou pro modely obtížnější než zprávy s odkazem a
   naléhavou výzvou k platbě.
3. **Dev, případy 9 a 11, Liquid:** Model vrátil platný JSON, ale zaměnil
   `investice` za `banka` a `vyhra` za `investice`. U případu 12 a 13 navíc
   upstream limit `429` zabránil odpovědi. Menší model měl problém rozlišit
   hlavní záměr podvodu a současně byl nejvíce ovlivněn sdíleným limitem.

## Doporučení

Pro nasazení na 10 000 SMS denně bych zvolil `cohere/north-mini-code:free`
nebo jeho placenou variantu. Na dev sadě měl stejnou úplnou přesnost jako
Nemotron (93,33 %), ale byl přibližně pětkrát rychlejší a použil výrazně méně
výstupních tokenů. V produkci by bylo nutné použít placený endpoint nebo vlastní
provider key, protože bezplatný OpenRouter limit není pro 10 000 zpráv denně
vhodný.

Pro orientační výpočet jsem použil naměřenou spotřebu nejlepšího běhu Cohere:
5 570 vstupních a 2 115 výstupních tokenů na 15 SMS. Pro 10 000 SMS by to
při stejném průměru znamenalo přibližně 3 713 333 vstupních a 1 410 000
výstupních tokenů. Placená Cohere varianta `cohere/command-r7b-12-2024` měla
v době měření na OpenRouteru cenu 0,0000000375 USD za vstupní token a
0,00000015 USD za výstupní token:

```text
3 713 333 × 0,0000000375 = 0,13925 USD
1 410 000 × 0,00000015   = 0,21150 USD
Celkem přibližně          = 0,35075 USD za 10 000 SMS
```

Jde o odhad pro placenou variantu, ne o cenu bezplatného modelu
`cohere/north-mini-code:free`; ceny poskytovatelů se mohou měnit.

## AI asistent a reflexe

OpenCode jsem používal pro pomoc s návrhem struktury projektu, JSONL dat,
promptů a evaluačního skriptu. Při práci jsem musel přepnout mezi poskytovateli,
protože Groq vracel 403, Gemini neměl dostupný zvolený model a OpenRouter měl
omezení bezplatných modelů. Nejvíce mě překvapilo, že rychlejší nebo větší
model automaticky neznamená lepší výsledek: Cohere a Nemotron měly stejnou
přesnost, ale výrazně odlišnou latenci a spotřebu tokenů. Příště bych hned na
začátku ověřil dostupnost všech modelů krátkým testem a nechal si větší rezervu
v denním limitu. Také bych před finálním měřením odstranil neúspěšné běhy ze
souhrnu a kontroloval, zda každý případ skutečně dostal odpověď.
