# Jídelníček: název jídla, alergeny (čísla)

## Popis nástroje
Nástroj slouží ke zpracování a strukturovanému zobrazení denního nabídkového menu školní jídelny. Umožňuje uživatelům snadno projít dostupná jídla včetně jejich názvu a přiřazených číselných kódů alergenů. Díky standardizovanému formátu usnadňuje filtrování pokrmů pro osoby se specifickými dietními omezeními

## Schéma výstupu
```json
{
  "nazev_jidla": "string",
  "kategorie": "polevka | hlavni_jidlo | dezert | napoj | jine",
  "alergeny": [ "number" ]
}
```

* **nazev_jidla – název pokrmu nebo nápoje, např. "Svíčková na smetaně", "Čočková polévka". null, pokud text název neuvádí.

* **kategorie – zařazení jídla do kategorie: polevka, hlavni_jidlo, dezert, napoj nebo jine. null, pokud ji nelze určit.

* **alergeny – pole číselných kódů alergenů (1–14) obsažených v pokrmu, např. [1, 3, 7]. Pokud pokrm žádné alergeny neobsahuje nebo nejsou uvedeny, vrací se prázdné pole [].

## Pravidla porovnávání

nazev_jidla: nerozlišuje se velikost písmen a přebytečné mezery na začátku/konci se ignorují ("svíčková" = "Svíčková" = " Svíčková ").

kategorie: porovnává se jako přesný řetězec z definovaného výčtu (polevka, hlavni_jidlo, dezert, napoj, jine).

alergeny: porovnává se jako množina čísel – na pořadí čísel v poli nezáleží, duplicity se ignorují a ignoruje se původní formátování zápisu v textu (např. "(1, 3, 7)" = "alergeny: 1,3,7" = [1, 3, 7])

## 1. Závěrečná zpráva a reflexe

## 1. Rozbor 3 chyb z dev sady
1. **Chybějící alergen v závorce**
   * **Vstup:** "Dnes nabízíme Hovězí guláš s knedlikiem, obsahující alergeny (1,3,7)"
   * **Model vrátil:** `[1, 3]` (chyběla sedmička)
   * **Správně:** `[1, 3, 7]`
   * **Proč:** Šlo o chybu modelu, který přehlédl poslední položku na konci závorky těsně před uzavřením.
2. **Neplatný JSON u chytáku**
   * **Vstup:** "Jako dezert máme svjčkovou na smetaně? Ne, kofolu!"
   * **Model vrátil:** Textové vysvětlení (omluvu a konverzační odpověď)
   * **Správně:** `{"nazev_jidla": "Kofola", "kategorie": "napoj", "alergeny": []}`
   * **Proč:** Nejasné zadání / chyták. Model sklouzl do chatovacího režimu místo dodržení formátu.
3. **Normalizace názvu jídla**
   * **Vstup:** "Máme dnes v jídelně řízek z kuřecího masa s kaši (1,3,7)..."
   * **Model vrátil:** `"řízek z kuřecího masa s kaši"`
   * **Správně:** `"Kuřecí řízek s bramborovou kaší"`
   * **Proč:** Chyba v mé správné odpovědi (gold) – očekával jsem standardizovaný název, ale v promptu jsem model neupozornil na normalizaci.

## 2. Doporučení pro produkční nasazení (10 000 dotazů denně)
* **Model a prompt:** Pro produkci bych zvolil model `gemini-2.5-flash` s přísnějším promptem (`v2`) a vynucením JSON struktury. Nabízí skvělý poměr rychlosti, nízké latence a vysoké přesnosti.
* **Cenová kalkulace:** Při průměrné spotřebě cca 160 vstupních a 40 výstupních tokenů na dotaz (pro 10 000 dotazů denně = 1,6M vstupních a 0,4M výstupních tokenů) a orientační ceně na OpenRouteru kolem $0.10 / 1M vstupních a $0.40 / 1M výstupních tokenů by 10 000 dotazů stálo zhruba **$0.32 denně** (cca 7–8 Kč).

### 3. Stav projektu a neprovedená Fáze 4
* **Rozdíl dev a test sady:** Testovací sadu (`test.jsonl`) a pokročilé experimenty (Fáze 4 – porovnání více modelů, iterace promptu na `v2` a finální měření na test sadě) **se mi kvůli časové tísni nepodařilo dokončit**. 
* Veškerá dosavadní měření proběhla na vývojové sadě (`dev.jsonl`) s použitím promptu `v1` a modelu `gemini-3.5-flash-lite`. Na `dev` sadě dosáhl model 100% validity JSON výstupů a 60% úplné shody.

## 4. AI asistent
Pro vývoj, ladění skriptu a tvorbu dat jsem používal model **Gemini (flash-lite)** v rozhraní OpenCode. Přepínat mezi modely nebylo nutné. Asistent mi obrovsky pomohl s napsáním Python skriptu, ošetřením chyb 429 a implementací mezipaměti (cache). Žádné zásadní selhání jsem nezaznamenal.

## 5. Reflexe
Celá praxe pro mě byla velmi přínosná a ukázala mi, jak funguje automatizované testování AI aplikací v praxi. Překvapilo mě, jak snadno dokáže model vypadnout z formátu JSON při nečekaném chytáku v textu. Ocenil jsem význam mezipaměti (cache), která obrovsky šetří čas i limity API při opakovaném spouštění. Kdybych měl úkol dělat znovu, lépe bych si rozvrhl čas, abych stihl dokončit i porovnání vícero modelů a druhou verzi promptu ve Fázi 4.