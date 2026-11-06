"""Pustí všechny experimenty z Fáze 4 a na konci vyrobí report.

    python src/run_all.py            # 4a + 4b na dev, pak 4c na test pro 2 nejlepší kombinace
    python src/run_all.py --jen-dev  # jen dev (test spustíš později)

1. Ověří klíče a spojení ke každému poskytovateli (bez spotřeby tokenů).
2. Z KANDIDATU vezme první 3 modely, které opravdu fungují (když jeden selže, nastoupí další).
3. 4a: prompt v1 na dev, 4b: prompt v2 na dev, 4c: 2 nejlepší kombinace na test.
Díky cache stojí opakované spuštění 0 požadavků – po chybě ho stačí pustit znovu.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval as ev  # noqa: E402
import report  # noqa: E402

# (poskytovatel, model) v pořadí, v jakém se zkoušejí. Potřebujeme 3 funkční,
# ideálně malý + velký model a aspoň 2 poskytovatele.
KANDIDATI = [
    ("groq", "openai/gpt-oss-20b"),                         # ~20 mld. parametrů
    ("groq", "openai/gpt-oss-120b"),                        # ~120 mld. parametrů
    ("mistral", "mistral-small-latest"),                    # jiný poskytovatel (~24 mld.)
    ("groq", "llama-3.1-8b-instant"),                       # záloha: malý model 8 mld.
    ("groq", "llama-3.3-70b-versatile"),                    # záloha: 70 mld.
    ("groq", "qwen/qwen3-32b"),                             # záloha: 32 mld.
    ("gemini", "gemini-flash-latest"),                      # záloha: jiný poskytovatel
]
POTREBA_MODELU = 3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jen-dev", action="store_true")
    a = ap.parse_args()
    ev.nacti_env()

    print("######## kontrola klíčů a spojení")
    dostupne = {}
    for posk in dict.fromkeys(p for p, _ in KANDIDATI):
        ok, info = ev.over_spojeni(posk)
        dostupne[posk] = info if ok else None
        print(f"  {posk:<10} {'OK' if ok else 'NEJDE: ' + info}")

    vybrane = []
    for posk, model in KANDIDATI:
        if dostupne.get(posk) is None:
            continue
        vybrane.append((posk, model))
    # další zálohy: chatovací modely, které Groq tomuhle účtu opravdu nabízí
    nechci = ("whisper", "tts", "guard", "compound", "orpheus", "playai", "distil")
    for model in dostupne.get("groq") or []:
        if model and not any(n in model.lower() for n in nechci) and ("groq", model) not in vybrane:
            vybrane.append(("groq", model))
    print("  pořadí modelů k vyzkoušení: " + ", ".join(m for _, m in vybrane))
    if not vybrane:
        sys.exit("\nNejde se připojit k žádnému poskytovateli – oprav klíče v .env nebo připojení k internetu.")

    # výsledky se pokaždé skládají znovu (z cache to nic nestojí), aby README přesně sedělo se results/
    for f in ev.ROOT.joinpath("results").glob("*.json"):
        f.unlink()

    print("\n######## 4a: porovnání modelů (v1, dev)")
    hotove, dev = [], []
    for posk, model in vybrane:
        if len(hotove) == POTREBA_MODELU:
            break
        b = ev.spust("dev", "v1", posk, model)
        if b:
            hotove.append((posk, model))
            dev.append(b)
        else:
            print(f"!! {model} ({posk}) nefunguje, zkouším další model")
    if len(hotove) < POTREBA_MODELU:
        print(f"!! Funkční jsou jen {len(hotove)} modely – spusť skript později znovu (hotové je v cache).")
    if not dev:
        sys.exit("Žádný běh neproběhl.")

    print("\n######## 4b: lepší prompt (v2, dev)")
    for posk, model in hotove:
        b = ev.spust("dev", "v2", posk, model)
        if b:
            dev.append(b)

    if not a.jen_dev:
        # 4c: dvě nejlepší kombinace podle úplné shody na dev (při shodě validita, pak latence)
        poradi = sorted(dev, key=lambda b: (-b["uplna_shoda"], -b["validni_json"], b["latence_s"]))
        print("\n######## 4c: finální měření na test sadě – 2 nejlepší kombinace z dev:")
        for b in poradi[:2]:
            print(f"   {b['model']} ({b['poskytovatel']}) + {b['prompt']}: úplná shoda dev {b['uplna_shoda']:.0%}")
        for b in poradi[:2]:
            ev.spust("test", b["prompt"], b["poskytovatel"], b["model"])

    report.main()
    print("\nHOTOVO.")


if __name__ == "__main__":
    main()
