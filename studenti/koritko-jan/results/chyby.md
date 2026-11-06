# Chybné případy

Vygenerováno skriptem `src/report.py` ze surových výsledků v `results/`.


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

## openai/gpt-oss-120b (groq), prompt v2, sada dev – 0 chyb z 15


## openai/gpt-oss-20b (groq), prompt v2, sada dev – 0 chyb z 15


## openai/gpt-oss-120b (groq), prompt v2, sada test – 0 chyb z 10


## openai/gpt-oss-20b (groq), prompt v2, sada test – 0 chyb z 10

