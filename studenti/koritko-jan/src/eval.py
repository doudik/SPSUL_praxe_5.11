"""Eval extrakce údajů ze zpráv o počasí.

Použití:
    python src/eval.py --sada dev --prompt v1 --poskytovatel groq --model openai/gpt-oss-20b

Jen standardní knihovna Pythonu, nic se neinstaluje.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

try:  # české znaky i ve Windows konzoli
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent  # studenti/koritko-jan
STUDENT = "Jan Koritko"
ULOHA = "Zprávy o počasí"
POLE = ["mesto", "teplota", "srazky", "typ_srazek"]
TYPY = {"dest", "snih", "dest_se_snehem", "bourka", "krupobiti", "zadne"}

POSKYTOVATELE = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "mistral": ("https://api.mistral.ai/v1", "MISTRAL_API_KEY"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
    "nvidia": ("https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY"),
}
# pauza mezi skutečnými požadavky (s), ať nenarážíme na limity tokenů/min
PAUZA = {"groq": 2.0, "mistral": 1.2, "gemini": 4.0, "openrouter": 3.5, "nvidia": 1.6}


# ---------------------------------------------------------------- pomocné

def nacti_env():
    """Načte .env ze složky projektu (bez knihovny python-dotenv)."""
    soubor = ROOT / ".env"
    if not soubor.exists():
        return
    for radek in soubor.read_text(encoding="utf-8-sig").splitlines():
        radek = radek.strip()
        if not radek or radek.startswith("#") or "=" not in radek:
            continue
        k, v = radek.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def nacti_sadu(sada):
    with open(ROOT / "data" / f"{sada}.jsonl", encoding="utf-8") as f:
        return [json.loads(r) for r in f if r.strip()]


def bez_diakritiky(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


# ---------------------------------------------------------------- volání API

def zavolej(poskytovatel, model, prompt_text, json_mode, max_pokusu=6):
    base_url, env_klic = POSKYTOVATELE[poskytovatel]
    klic = os.environ.get(env_klic)
    if not klic:
        sys.exit(f"Chybí {env_klic} v .env (viz .env.example).")
    telo = {
        "model": model,
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0,
    }
    if json_mode:
        telo["response_format"] = {"type": "json_object"}
    data = json.dumps(telo).encode("utf-8")
    for pokus in range(1, max_pokusu + 1):
        req = urllib.request.Request(
            base_url.rstrip("/") + "/chat/completions",
            data=data,
            headers={"Authorization": f"Bearer {klic}", "Content-Type": "application/json",
                     "User-Agent": "spsul-eval"},
        )
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                odpoved = json.loads(r.read().decode("utf-8"))
            latence = time.perf_counter() - start
            return odpoved, latence
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")[:300]
            if e.code in (429, 500, 502, 503, 504) and pokus < max_pokusu:
                cekej = float(e.headers.get("retry-after") or 0) or min(10 * pokus, 60)
                print(f"    HTTP {e.code}, čekám {cekej:.0f} s a zkouším znovu ({pokus}/{max_pokusu})")
                time.sleep(cekej)
                continue
            raise RuntimeError(f"HTTP {e.code}: {text}") from None
        except (urllib.error.URLError, TimeoutError) as e:
            if pokus < max_pokusu:
                print(f"    síťová chyba {e}, zkouším znovu")
                time.sleep(5 * pokus)
                continue
            raise


def zavolej_s_cache(poskytovatel, model, prompt_text, json_mode):
    """Vrátí (odpoved, latence, z_cache). Klíč = hash(poskytovatel + model + celý prompt se vstupem)."""
    klic = hashlib.sha256(f"{poskytovatel}|{model}|{json_mode}|{prompt_text}".encode("utf-8")).hexdigest()
    cache_dir = ROOT / "cache"
    cache_dir.mkdir(exist_ok=True)
    soubor = cache_dir / f"{klic}.json"
    if soubor.exists():
        ulozene = json.loads(soubor.read_text(encoding="utf-8"))
        return ulozene["odpoved"], ulozene["latence_s"], True
    odpoved, latence = zavolej(poskytovatel, model, prompt_text, json_mode)
    soubor.write_text(json.dumps({"odpoved": odpoved, "latence_s": latence}, ensure_ascii=False),
                      encoding="utf-8")
    return odpoved, latence, False


# ---------------------------------------------------------------- parsování a porovnání

def rozparsuj(text):
    """Zkusí z odpovědi modelu dostat JSON objekt. Vrátí dict, nebo None (= nevalidní výstup)."""
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)  # odstraní ```json ... ```
    try:
        obj = json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", t, re.S)  # první {...} v textu
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return obj if isinstance(obj, dict) else None


def norm_mesto(v):
    if v is None:
        return None
    if not isinstance(v, str):
        return "__spatny_typ__"
    v = bez_diakritiky(v).lower().strip()
    v = re.sub(r"[\s\-–]+", " ", v)
    return v or None


def norm_teplota(v):
    if v is None or isinstance(v, bool):
        return None if v is None else "__spatny_typ__"
    if isinstance(v, (int, float)):
        return round(v)
    if isinstance(v, str):  # model vrátil "14 °C" nebo "-3"
        m = re.search(r"[-−]?\d+(?:[.,]\d+)?", v)
        if v.strip().lower() in ("", "null", "none"):
            return None
        if m:
            return round(float(m.group(0).replace("−", "-").replace(",", ".")))
    return "__spatny_typ__"


def norm_srazky(v):
    if v is None or isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "ano", "yes"):
            return True
        if s in ("false", "ne", "no"):
            return False
        if s in ("null", "none", ""):
            return None
    return "__spatny_typ__"


def norm_typ(v):
    if v is None:
        return None
    if not isinstance(v, str):
        return "__spatny_typ__"
    s = bez_diakritiky(v).lower().strip().replace(" ", "_")
    return None if s in ("null", "none", "") else s


NORM = {"mesto": norm_mesto, "teplota": norm_teplota, "srazky": norm_srazky, "typ_srazek": norm_typ}


def porovnej(vystup, expected):
    """Vrátí {pole: True/False}. Nevalidní výstup = všechna pole špatně."""
    if vystup is None:
        return {p: False for p in POLE}
    return {p: NORM[p](vystup.get(p)) == NORM[p](expected.get(p)) for p in POLE}


# ---------------------------------------------------------------- hlavní běh

def bezpecne_jmeno(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)


def uloz_summary(beh):
    soubor = ROOT / "results" / "summary.json"
    if soubor.exists():
        summary = json.loads(soubor.read_text(encoding="utf-8"))
    else:
        summary = {"student": STUDENT, "uloha": ULOHA, "behy": []}
    summary["student"], summary["uloha"] = STUDENT, ULOHA
    klic = lambda b: (b["model"], b["poskytovatel"], b["prompt"], b["sada"])
    summary["behy"] = [b for b in summary.get("behy", []) if klic(b) != klic(beh)] + [beh]
    summary["behy"].sort(key=lambda b: (b["sada"], b["prompt"], b["poskytovatel"], b["model"]))
    soubor.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def spust(sada, prompt, poskytovatel, model, json_mode=False):
    nacti_env()
    if poskytovatel not in POSKYTOVATELE:
        sys.exit(f"Neznámý poskytovatel {poskytovatel}. Možnosti: {', '.join(POSKYTOVATELE)}")
    sablona = (ROOT / "prompts" / f"{prompt}.txt").read_text(encoding="utf-8")
    pripady = nacti_sadu(sada)
    print(f"== {model} ({poskytovatel}), prompt {prompt}, sada {sada}, {len(pripady)} případů")

    zaznamy, volani_api, chyb_api = [], 0, 0
    for p in pripady:
        prompt_text = sablona.replace("{text}", p["input"])
        try:
            odpoved, latence, z_cache = zavolej_s_cache(poskytovatel, model, prompt_text, json_mode)
        except Exception as e:  # chyba API nesmí shodit celý běh
            print(f"  #{p['id']}: CHYBA API {e}")
            odpoved, latence, z_cache = None, 0.0, True  # chybu necachujeme, ale ani nečekáme
            chyb_api += 1
            if "HTTP 4" in str(e) and "HTTP 429" not in str(e):
                print("  Chyba 4xx (špatný klíč nebo název modelu) – běh přerušen, nic se neukládá.")
                return None
        if not z_cache:
            volani_api += 1
            time.sleep(PAUZA.get(poskytovatel, 1.0))
        text = None
        usage = {}
        if odpoved:
            try:
                text = odpoved["choices"][0]["message"].get("content")
            except (KeyError, IndexError, TypeError):
                text = None
            usage = odpoved.get("usage") or {}
        vystup = rozparsuj(text)
        shody = porovnej(vystup, p["expected"])
        zaznamy.append({
            "id": p["id"], "tezky": p.get("tezky", False), "input": p["input"],
            "expected": p["expected"], "raw": text, "parsed": vystup,
            "validni": vystup is not None, "shody": shody, "vse": all(shody.values()),
            "latence_s": round(latence, 3), "z_cache": z_cache,
            "prompt_tokens": usage.get("prompt_tokens", 0) or 0,
            "completion_tokens": usage.get("completion_tokens", 0) or 0,
        })
        znacka = "OK " if all(shody.values()) else ("NEV" if vystup is None else "-- ")
        print(f"  #{p['id']:>2} {znacka} {'(cache)' if z_cache else f'{latence:.2f}s'}  {json.dumps(vystup, ensure_ascii=False)}")

    if chyb_api:
        print(f"!! {chyb_api} požadavků selhalo – běh se neukládá, spusť ho znovu (hotové odpovědi jsou v cache).")
        return None
    n = len(zaznamy)
    beh = {
        "model": model,
        "poskytovatel": poskytovatel,
        "prompt": prompt,
        "sada": sada,
        "pripadu": n,
        "validni_json": round(sum(z["validni"] for z in zaznamy) / n, 4),
        "uplna_shoda": round(sum(z["vse"] for z in zaznamy) / n, 4),
        "pole": {f: round(sum(z["shody"][f] for z in zaznamy) / n, 4) for f in POLE},
        "latence_s": round(sum(z["latence_s"] for z in zaznamy) / n, 3),
        "tokeny_vstup": sum(z["prompt_tokens"] for z in zaznamy),
        "tokeny_vystup": sum(z["completion_tokens"] for z in zaznamy),
    }

    vysl = ROOT / "results"
    vysl.mkdir(exist_ok=True)
    jmeno = f"{sada}_{prompt}_{poskytovatel}_{bezpecne_jmeno(model)}.json"
    (vysl / jmeno).write_text(json.dumps({"souhrn": beh, "pripady": zaznamy}, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
    uloz_summary(beh)

    print(f"-- validní JSON {beh['validni_json']:.0%} | úplná shoda {beh['uplna_shoda']:.0%} | "
          + " | ".join(f"{k} {v:.0%}" for k, v in beh["pole"].items()))
    print(f"-- latence {beh['latence_s']:.2f} s | tokeny {beh['tokeny_vstup']} / {beh['tokeny_vystup']} | "
          f"nových volání API: {volani_api} | uloženo results/{jmeno}\n")
    return beh


def main():
    ap = argparse.ArgumentParser(description="Eval extrakce ze zpráv o počasí")
    ap.add_argument("--sada", choices=["dev", "test"], default="dev")
    ap.add_argument("--prompt", default="v1", help="název souboru v prompts/ bez .txt")
    ap.add_argument("--poskytovatel", default="groq", choices=list(POSKYTOVATELE))
    ap.add_argument("--model", default="openai/gpt-oss-20b")
    ap.add_argument("--json-mode", action="store_true", help='pošle response_format={"type":"json_object"}')
    a = ap.parse_args()
    spust(a.sada, a.prompt, a.poskytovatel, a.model, a.json_mode)


if __name__ == "__main__":
    main()
