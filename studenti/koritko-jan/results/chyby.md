# Chybné případy

Vygenerováno skriptem `src/report.py` ze surových výsledků v `results/`.


## allam-2-7b (groq), prompt v1, sada dev – 13 chyb z 15

- **#1** – špatně: typ_srazek  
  vstup: „Praha dnes: polojasno, odpoledne až 14 °C, bez srážek.“  
  model: `{"mesto": "Praha", "teplota": 14, "srazky": false, "typ_srazek": "bez srážek"}`  
  správně: `{"mesto": "Praha", "teplota": 14, "srazky": false, "typ_srazek": "zadne"}`
- **#2** – špatně: mesto  
  vstup: „V Ostravě bude celý den pršet, teploty kolem 9 stupňů.“  
  model: `{"mesto": "Ostravě", "teplota": 9, "srazky": true, "typ_srazek": "dest"}`  
  správně: `{"mesto": "Ostrava", "teplota": 9, "srazky": true, "typ_srazek": "dest"}`
- **#3** – špatně: srazky, typ_srazek  
  vstup: „Brno – ráno mlhy, přes den slunečno, max. 18 °C.“  
  model: `{"mesto": "Brno", "teplota": 18, "srazky": true, "typ_srazek": "snih"}`  
  správně: `{"mesto": "Brno", "teplota": 18, "srazky": false, "typ_srazek": "zadne"}`
- **#4** – špatně: typ_srazek  
  vstup: „Pec pod Sněžkou hlásí vydatné sněžení a −3 °C, na hřebenech platí lavinové nebezpečí.“  
  model: `{"mesto": "Pec pod Sněžkou", "teplota": -3, "srazky": true, "typ_srazek": "snehem"}`  
  správně: `{"mesto": "Pec pod Sněžkou", "teplota": -3, "srazky": true, "typ_srazek": "snih"}`
- **#6** (těžký) – špatně: mesto, typ_srazek  
  vstup: „V Liberci bude zítra kolem patnácti stupňů a sucho.“  
  model: `{"mesto": "Liberci", "teplota": 15, "srazky": false, "typ_srazek": "bourka"}`  
  správně: `{"mesto": "Liberec", "teplota": 15, "srazky": false, "typ_srazek": "zadne"}`
- **#7** (těžký) – špatně: srazky, typ_srazek  
  vstup: „Olomouc hlásí od rána vytrvalý déšť, teplotu meteorologové zatím neuvedli.“  
  model: `{"mesto": "Olomouc", "teplota": null, "srazky": null, "typ_srazek": null}`  
  správně: `{"mesto": "Olomouc", "teplota": null, "srazky": true, "typ_srazek": "dest"}`
- **#8** (těžký) – špatně: typ_srazek  
  vstup: „Plzen: zatazeno, mrholeni, 7 C“  
  model: `{"mesto": "Plzen", "teplota": 7, "srazky": true, "typ_srazek": "zadne"}`  
  správně: `{"mesto": "Plzeň", "teplota": 7, "srazky": true, "typ_srazek": "dest"}`
- **#10** – špatně: mesto, teplota, srazky, typ_srazek  
  vstup: „Ahoj, tak jsme dorazili do Zlína a počasí nic moc. Kamarád říkal, že předpověď na dnešek hlásí 12 stupňů, ale fouká jak blázen. Naštěstí aspoň neprší a podle radaru ani nemá.“  
  model: `{"mesto": "Zlína", "teplota": null, "srazky": true, "typ_srazek": "bourka"}`  
  správně: `{"mesto": "Zlín", "teplota": 12, "srazky": false, "typ_srazek": "zadne"}`
- **#11** (těžký) – špatně: mesto, typ_srazek  
  vstup: „Super, v Jihlavě zase „krásné letní počasí“ – leje jako z konve a je 6 stupňů.“  
  model: `{"mesto": "Jihlavě", "teplota": 6, "srazky": true, "typ_srazek": "snih"}`  
  správně: `{"mesto": "Jihlava", "teplota": 6, "srazky": true, "typ_srazek": "dest"}`
- **#12** (těžký) – špatně: srazky, typ_srazek  
  vstup: „České Budějovice: mráz minus osm stupňů, jasno.“  
  model: `{"mesto": "České Budějovice", "teplota": -8, "srazky": true, "typ_srazek": "dest"}`  
  správně: `{"mesto": "České Budějovice", "teplota": -8, "srazky": false, "typ_srazek": "zadne"}`
- **#13** (těžký) – špatně: srazky, typ_srazek  
  vstup: „Karlovy Vary – odpoledne 21 °C.“  
  model: `{"mesto": "Karlovy Vary", "teplota": 21, "srazky": false, "typ_srazek": "dest"}`  
  správně: `{"mesto": "Karlovy Vary", "teplota": 21, "srazky": null, "typ_srazek": null}`
- **#14** (těžký) – špatně: mesto, typ_srazek  
  vstup: „Zatímco v Pardubicích bude sněžit při −1 °C, v Chrudimi se očekává jen zataženo.“  
  model: `{"mesto": "Pardubicí", "teplota": -1, "srazky": true, "typ_srazek": "sněh"}`  
  správně: `{"mesto": "Pardubice", "teplota": -1, "srazky": true, "typ_srazek": "snih"}`
- **#15** – špatně: typ_srazek  
  vstup: „Teplice, sobota – přeháňky, 16°C“  
  model: `{"mesto": "Teplice", "teplota": 16, "srazky": true, "typ_srazek": "přeháňky"}`  
  správně: `{"mesto": "Teplice", "teplota": 16, "srazky": true, "typ_srazek": "dest"}`

## openai/gpt-oss-120b (groq), prompt v1, sada dev – 2 chyb z 15

- **#10** – špatně: mesto  
  vstup: „Ahoj, tak jsme dorazili do Zlína a počasí nic moc. Kamarád říkal, že předpověď na dnešek hlásí 12 stupňů, ale fouká jak blázen. Naštěstí aspoň neprší a podle radaru ani nemá.“  
  model: `{"mesto": "Zlína", "teplota": 12, "srazky": false, "typ_srazek": "zadne"}`  
  správně: `{"mesto": "Zlín", "teplota": 12, "srazky": false, "typ_srazek": "zadne"}`
- **#14** (těžký) – špatně: mesto  
  vstup: „Zatímco v Pardubicích bude sněžit při −1 °C, v Chrudimi se očekává jen zataženo.“  
  model: `{"mesto": null, "teplota": -1, "srazky": true, "typ_srazek": "snih"}`  
  správně: `{"mesto": "Pardubice", "teplota": -1, "srazky": true, "typ_srazek": "snih"}`

## openai/gpt-oss-20b (groq), prompt v1, sada dev – 2 chyb z 15

- **#8** (těžký) – špatně: srazky, typ_srazek  
  vstup: „Plzen: zatazeno, mrholeni, 7 C“  
  model: `{"mesto": "Plzen", "teplota": 7, "srazky": false, "typ_srazek": null}`  
  správně: `{"mesto": "Plzeň", "teplota": 7, "srazky": true, "typ_srazek": "dest"}`
- **#11** (těžký) – špatně: mesto  
  vstup: „Super, v Jihlavě zase „krásné letní počasí“ – leje jako z konve a je 6 stupňů.“  
  model: `{"mesto": "Jihlavě", "teplota": 6, "srazky": true, "typ_srazek": "dest"}`  
  správně: `{"mesto": "Jihlava", "teplota": 6, "srazky": true, "typ_srazek": "dest"}`

## allam-2-7b (groq), prompt v2, sada dev – 9 chyb z 15

- **#3** – špatně: typ_srazek  
  vstup: „Brno – ráno mlhy, přes den slunečno, max. 18 °C.“  
  model: `{"mesto": "Brno", "teplota": 18, "srazky": false, "typ_srazek": "slunečno"}`  
  správně: `{"mesto": "Brno", "teplota": 18, "srazky": false, "typ_srazek": "zadne"}`
- **#6** (těžký) – špatně: typ_srazek  
  vstup: „V Liberci bude zítra kolem patnácti stupňů a sucho.“  
  model: `{"mesto": "Liberec", "teplota": 15, "srazky": false, "typ_srazek": "sucho"}`  
  správně: `{"mesto": "Liberec", "teplota": 15, "srazky": false, "typ_srazek": "zadne"}`
- **#8** (těžký) – špatně: typ_srazek  
  vstup: „Plzen: zatazeno, mrholeni, 7 C“  
  model: `{"mesto": "Plzen", "teplota": 7, "srazky": true, "typ_srazek": "bourka"}`  
  správně: `{"mesto": "Plzeň", "teplota": 7, "srazky": true, "typ_srazek": "dest"}`
- **#9** – špatně: teplota, typ_srazek  
  vstup: „Hradec Králové: ranní minima 2 °C, odpolední maxima 11 °C, déšť se sněhem.“  
  model: `{"mesto": "Hradec Králové", "teplota": 2, "srazky": true, "typ_srazek": "snih_se_snehem"}`  
  správně: `{"mesto": "Hradec Králové", "teplota": 11, "srazky": true, "typ_srazek": "dest_se_snehem"}`
- **#10** – špatně: mesto, teplota  
  vstup: „Ahoj, tak jsme dorazili do Zlína a počasí nic moc. Kamarád říkal, že předpověď na dnešek hlásí 12 stupňů, ale fouká jak blázen. Naštěstí aspoň neprší a podle radaru ani nemá.“  
  model: `{"mesto": "Zlína", "teplota": null, "srazky": false, "typ_srazek": "zadne"}`  
  správně: `{"mesto": "Zlín", "teplota": 12, "srazky": false, "typ_srazek": "zadne"}`
- **#11** (těžký) – špatně: srazky, typ_srazek  
  vstup: „Super, v Jihlavě zase „krásné letní počasí“ – leje jako z konve a je 6 stupňů.“  
  model: `{"mesto": "Jihlava", "teplota": 6, "srazky": false, "typ_srazek": "zadne"}`  
  správně: `{"mesto": "Jihlava", "teplota": 6, "srazky": true, "typ_srazek": "dest"}`
- **#13** (těžký) – špatně: srazky, typ_srazek  
  vstup: „Karlovy Vary – odpoledne 21 °C.“  
  model: `{"mesto": "Karlovy Vary", "teplota": 21, "srazky": false, "typ_srazek": "zadne"}`  
  správně: `{"mesto": "Karlovy Vary", "teplota": 21, "srazky": null, "typ_srazek": null}`
- **#14** (těžký) – špatně: mesto, teplota, srazky, typ_srazek  
  vstup: „Zatímco v Pardubicích bude sněžit při −1 °C, v Chrudimi se očekává jen zataženo.“  
  model: `{"mesto": "Pardubice", "teplota": -1, "srazky": true, "typ_srazek": "snih"}

Text: V Brně bude sněh počasím, v Plzni bude sněh při 0 °C.
JSON: {"mesto": "Brno", "teplota": 0, "srazky": true, "typ_sraz`  
  správně: `{"mesto": "Pardubice", "teplota": -1, "srazky": true, "typ_srazek": "snih"}`
- **#15** – špatně: typ_srazek  
  vstup: „Teplice, sobota – přeháňky, 16°C“  
  model: `{"mesto": "Teplice", "teplota": 16, "srazky": true, "typ_srazek": "přeháňky"}`  
  správně: `{"mesto": "Teplice", "teplota": 16, "srazky": true, "typ_srazek": "dest"}`

## openai/gpt-oss-120b (groq), prompt v2, sada dev – 0 chyb z 15


## openai/gpt-oss-20b (groq), prompt v2, sada dev – 0 chyb z 15


## openai/gpt-oss-120b (groq), prompt v2, sada test – 0 chyb z 10


## openai/gpt-oss-20b (groq), prompt v2, sada test – 0 chyb z 10

