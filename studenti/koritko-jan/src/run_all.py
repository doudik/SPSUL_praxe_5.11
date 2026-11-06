"""Pustí všechny experimenty z Fáze 4 a na konci vyrobí report.

    python src/run_all.py            # 4a + 4b na dev, pak 4c na test pro 2 nejlepší kombinace
    python src/run_all.py --jen-dev  # jen dev (test spustíš později)

Modely se nastavují v MODELY níže (ne v kódu evalu). Poskytovatel bez klíče v .env se přeskočí.
Díky cache stojí opakované spuštění 0 požadavků.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval as ev  # noqa: E402
import report  # noqa: E402

# (poskytovatel, model) – malý, velký a model od jiného poskytovatele
MODELY = [
    ("groq", "openai/gpt-oss-20b"),          # ~20 mld. parametrů
    ("groq", "llama-3.3-70b-versatile"),     # 70 mld. parametrů
    ("mistral", "mistral-small-latest"),     # jiný poskytovatel (~24 mld.)
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jen-dev", action="store_true")
    a = ap.parse_args()
    ev.nacti_env()

    modely = []
    for posk, model in MODELY:
        if os.environ.get(ev.POSKYTOVATELE[posk][1]):
            modely.append((posk, model))
        else:
            print(f"!! přeskakuji {model}: chybí {ev.POSKYTOVATELE[posk][1]} v .env")
    if not modely:
        sys.exit("Žádný klíč v .env – nejdřív vyplň .env (viz .env.example).")

    dev = []
    print("\n######## 4a: porovnání modelů (v1, dev)")
    for posk, model in modely:
        dev.append(ev.spust("dev", "v1", posk, model))
    print("\n######## 4b: lepší prompt (v2, dev)")
    for posk, model in modely:
        dev.append(ev.spust("dev", "v2", posk, model))

    if not a.jen_dev:
        # 4c: dvě nejlepší kombinace podle úplné shody na dev (při shodě rozhoduje validita, pak latence)
        poradi = sorted(dev, key=lambda b: (-b["uplna_shoda"], -b["validni_json"], b["latence_s"]))
        print("\n######## 4c: finální měření na test sadě – 2 nejlepší kombinace z dev:")
        for b in poradi[:2]:
            print(f"   {b['model']} ({b['poskytovatel']}) + {b['prompt']}: úplná shoda dev {b['uplna_shoda']:.0%}")
        for b in poradi[:2]:
            ev.spust("test", b["prompt"], b["poskytovatel"], b["model"])

    report.main()


if __name__ == "__main__":
    main()
