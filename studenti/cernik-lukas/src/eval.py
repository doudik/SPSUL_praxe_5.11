#!/usr/bin/env python3
"""
Evaluační skript pro úlohu: Extrakce strukturovaných dat z bug reportů.
Měří úspěšnost LLM modelů na testovací sadě (dev / test).
Podporuje cache, ošetření rate limitů (429), výpočet metrik a zápis do summary.json pro dashboard.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# Cesty k důležitým adresářům (relativně k umístění tohoto skriptu)
BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
DATA_DIR = BASE_DIR / "data"
PROMPTS_DIR = BASE_DIR / "prompts"
RESULTS_DIR = BASE_DIR / "results"

STUDENT_NAME = "Lukáš Černík"
ULOHA_NAME = "Bug reporty"

# Poskytovatelé a jejich výchozí konfigurace
PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "env_key": "GROQ_API_KEY",
        "default_model": "openai/gpt-oss-20b",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "env_key": "MISTRAL_API_KEY",
        "default_model": "mistral-small-latest",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "env_key": "GEMINI_API_KEY",
        "default_model": "gemini-2.5-flash",
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "env_key": "GEMINI_API_KEY",
        "default_model": "gemini-2.5-flash",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "default_model": "meta-llama/llama-3.3-70b-instruct:free",
    },
}


def load_env_file(env_path: Path):
    """Načte proměnné prostředí ze souboru .env bez nutnosti externí knihovny."""
    if not env_path.exists():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            if k and k not in os.environ:
                os.environ[k] = v


def compute_cache_key(provider: str, model: str, prompt_text: str, input_text: str) -> str:
    """Vypočítá SHA-256 hash z kombinace provider + model + prompt + input."""
    raw = f"{provider}|{model}|{prompt_text}|{input_text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def call_llm_api(provider: str, model: str, prompt_text: str, input_text: str, api_key: str, max_retries: int = 5):
    """
    Odešle požadavek na OpenAI-kompatibilní API.
    Ošetřuje HTTP 429 (rate limit) a vrací odpověď, tokeny a latenci.
    """
    cfg = PROVIDERS.get(provider.lower())
    if not cfg:
        raise ValueError(f"Neznámý poskytovatel: {provider}. Podporovaní: {list(PROVIDERS.keys())}")

    url = f"{cfg['base_url'].rstrip('/')}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": prompt_text},
            {"role": "user", "content": input_text},
        ],
    }

    req_data = json.dumps(payload).encode("utf-8")

    for attempt in range(1, max_retries + 1):
        try:
            start_time = time.time()
            req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                elapsed = time.time() - start_time
                resp_body = resp.read().decode("utf-8")
                data = json.loads(resp_body)
                
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                
                return {
                    "raw_response": content,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "latency_s": elapsed,
                }
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="replace")
            if e.code == 429:
                wait_s = 10 * attempt
                print(f" [429 Rate Limit] Čekám {wait_s}s před dalším pokusem ({attempt}/{max_retries})...")
                time.sleep(wait_s)
                continue
            else:
                print(f" HTTP Error {e.code}: {err_msg}")
                raise
        except Exception as e:
            if attempt < max_retries:
                wait_s = 3 * attempt
                print(f" Chyba spojení: {e}. Zkouším znovu za {wait_s}s ({attempt}/{max_retries})...")
                time.sleep(wait_s)
                continue
            raise

    raise RuntimeError(f"Požadavek selhal i po {max_retries} pokusech.")


def extract_json_object(raw_text: str):
    """
    Zkusí rozparsovat text jako JSON. Pokud selže, pokusí se najít markdown blok ```json ... ```
    nebo první uzavřený složený závorkový blok {...}.
    """
    if not raw_text:
        return None

    cleaned = raw_text.strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Markdown blok ```json ... ```
    md_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if md_match:
        try:
            return json.loads(md_match.group(1).strip())
        except Exception:
            pass

    # První { a poslední }
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except Exception:
            pass

    return None


def normalize_bool(val):
    """Normalizuje hodnotu na boolean nebo None."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        v = val.strip().lower()
        if v in ("true", "1", "ano", "yes"):
            return True
        if v in ("false", "0", "ne", "no"):
            return False
        if v in ("null", "none", "neni", ""):
            return None
    return None


def normalize_str(val):
    """Normalizuje řetězec nebo None."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def evaluate_case(predicted_dict, expected_dict):
    """
    Vyhodnotí shodu předpovědi modelu s referenční odpovědí (expected)
    podle pravidel v README.md pro úlohu Bug reporty.
    """
    if not isinstance(predicted_dict, dict):
        return {
            "valid_json": False,
            "komponenta": False,
            "zavaznost": False,
            "reprodukovatelny": False,
            "chybova_hlaska": False,
            "uplna_shoda": False,
        }

    # 1. Komponenta (case-insensitive, strip)
    pred_komp = (str(predicted_dict.get("komponenta") or "")).strip().lower()
    exp_komp = (str(expected_dict.get("komponenta") or "")).strip().lower()
    match_komp = pred_komp == exp_komp

    # 2. Závažnost (case-insensitive, strip)
    pred_zav = (str(predicted_dict.get("zavaznost") or "")).strip().lower()
    exp_zav = (str(expected_dict.get("zavaznost") or "")).strip().lower()
    match_zav = pred_zav == exp_zav

    # 3. Reprodukovatelný (bool nebo None)
    pred_rep = normalize_bool(predicted_dict.get("reprodukovatelny"))
    exp_rep = normalize_bool(expected_dict.get("reprodukovatelny"))
    match_rep = pred_rep == exp_rep

    # 4. Chybová hláška (null vs null, nebo podřetězec / rovnost)
    pred_err = normalize_str(predicted_dict.get("chybova_hlaska"))
    exp_err = normalize_str(expected_dict.get("chybova_hlaska"))

    if exp_err is None:
        match_err = pred_err is None or pred_err.lower() in ("null", "none", "")
    else:
        if pred_err is None:
            match_err = False
        else:
            p_low = pred_err.lower()
            e_low = exp_err.lower()
            # Uznáme shodu, pokud je identická nebo jedna obsahuje druhou (např. '500' v '500 Internal Server Error')
            match_err = (p_low == e_low) or (e_low in p_low) or (p_low in e_low)

    all_matched = match_komp and match_zav and match_rep and match_err

    return {
        "valid_json": True,
        "komponenta": match_komp,
        "zavaznost": match_zav,
        "reprodukovatelny": match_rep,
        "chybova_hlaska": match_err,
        "uplna_shoda": all_matched,
    }


def save_summary_result(summary_file: Path, run_record: dict):
    """
    Zapíše nebo aktualizuje záznam v summary.json přesně dle specifikace dashboardu třídy.
    Pokud už záznam se stejným (model, poskytovatel, prompt, sada) existuje, přepíše ho.
    """
    summary_data = {
        "student": STUDENT_NAME,
        "uloha": ULOHA_NAME,
        "behy": [],
    }

    if summary_file.exists():
        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict) and "behy" in loaded:
                    summary_data = loaded
        except Exception as e:
            print(f"Varování: Nelze načíst existující {summary_file}: {e}")

    # Aktualizace nebo vložení
    key_fields = ("model", "poskytovatel", "prompt", "sada")
    found_idx = -1
    for i, b in enumerate(summary_data.get("behy", [])):
        if all(b.get(k) == run_record.get(k) for k in key_fields):
            found_idx = i
            break

    if found_idx >= 0:
        summary_data["behy"][found_idx] = run_record
    else:
        summary_data.setdefault("behy", []).append(run_record)

    summary_file.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Evaluační skript pro extrakci dat z bug reportů.")
    parser.add_argument("--provider", default="groq", choices=list(PROVIDERS.keys()), help="Poskytovatel API (groq, mistral, gemini, openrouter)")
    parser.add_argument("--model", default=None, help="Název modelu (pokud není zadán, použije se výchozí pro poskytovatele)")
    parser.add_argument("--dataset", default="dev", choices=["dev", "test"], help="Datová sada (dev nebo test)")
    parser.add_argument("--prompt", default="v1", help="Název promptu bez přípony (např. v1 nebo v2)")
    parser.add_argument("--limit", type=int, default=None, help="Volitelně omezí počet zpracovaných případů")
    parser.add_argument("--delay", type=float, default=0.5, help="Pauza mezi neuloženými API požadavky v sekundách")
    parser.add_argument("--no-cache", action="store_true", help="Vypne načítání z cache")
    args = parser.parse_args()

    # Načtení proměnných z .env
    load_env_file(BASE_DIR / ".env")

    provider = args.provider.lower()
    prov_cfg = PROVIDERS[provider]
    model = args.model or prov_cfg["default_model"]
    api_key = os.environ.get(prov_cfg["env_key"])

    if not api_key:
        print(f"CHYBA: Není nastaven API klíč pro {provider} v proměnné prostředí {prov_cfg['env_key']}.")
        print(f"Ujisti se, že soubor {BASE_DIR / '.env'} obsahuje {prov_cfg['env_key']}=<tvuj_klic>.")
        sys.exit(1)

    # Cesty k souborům
    prompt_file = PROMPTS_DIR / f"{args.prompt}.txt"
    dataset_file = DATA_DIR / f"{args.dataset}.jsonl"

    if not prompt_file.exists():
        print(f"CHYBA: Soubor s promptem neexistuje: {prompt_file}")
        sys.exit(1)

    if not dataset_file.exists():
        print(f"CHYBA: Soubor se sadou neexistuje: {dataset_file}")
        sys.exit(1)

    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt_text = f.read().strip()

    cases = []
    with open(dataset_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))

    if args.limit:
        cases = cases[: args.limit]

    total_cases = len(cases)
    print("=" * 70)
    print(f"Spouštím eval: Poskytovatel={provider.upper()}, Model={model}")
    print(f"Prompt={args.prompt}, Sada={args.dataset} ({total_cases} případů)")
    print("=" * 70)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    raw_results = []
    total_valid_json = 0
    total_uplna_shoda = 0
    field_matches = {
        "komponenta": 0,
        "zavaznost": 0,
        "reprodukovatelny": 0,
        "chybova_hlaska": 0,
    }
    total_latency = 0.0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    cache_hits = 0

    for idx, case in enumerate(cases, 1):
        case_id = case.get("id", idx)
        input_text = case["input"]
        expected = case["expected"]
        is_tezky = case.get("tezky", False)

        cache_key = compute_cache_key(provider, model, prompt_text, input_text)
        cache_path = CACHE_DIR / f"{cache_key}.json"

        call_data = None
        from_cache = False

        if not args.no_cache and cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    call_data = json.load(f)
                    from_cache = True
                    cache_hits += 1
            except Exception:
                call_data = None

        if call_data is None:
            call_data = call_llm_api(provider, model, prompt_text, input_text, api_key)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(call_data, f, ensure_ascii=False, indent=2)
            if args.delay > 0 and idx < total_cases:
                time.sleep(args.delay)

        raw_response = call_data.get("raw_response", "")
        parsed_json = extract_json_object(raw_response)
        eval_res = evaluate_case(parsed_json, expected)

        # Kumulace metrik
        total_latency += call_data.get("latency_s", 0.0)
        total_prompt_tokens += call_data.get("prompt_tokens", 0)
        total_completion_tokens += call_data.get("completion_tokens", 0)

        if eval_res["valid_json"]:
            total_valid_json += 1
        if eval_res["uplna_shoda"]:
            total_uplna_shoda += 1

        for field in field_matches:
            if eval_res[field]:
                field_matches[field] += 1

        status_tag = "OK" if eval_res["uplna_shoda"] else ("CHYBA" if eval_res["valid_json"] else "NEVALIDNÍ JSON")
        cache_tag = "[CACHE]" if from_cache else "[API]  "
        heavy_tag = "[ZÁLUDNÝ]" if is_tezky else "         "
        print(f"#{case_id:02d} {cache_tag} {heavy_tag} -> {status_tag}")

        raw_results.append({
            "id": case_id,
            "tezky": is_tezky,
            "input": input_text,
            "expected": expected,
            "raw_response": raw_response,
            "parsed": parsed_json,
            "evaluation": eval_res,
            "latency_s": call_data.get("latency_s", 0.0),
            "prompt_tokens": call_data.get("prompt_tokens", 0),
            "completion_tokens": call_data.get("completion_tokens", 0),
            "from_cache": from_cache,
        })

    # Výpočet podílů pro summary (hodnoty od 0 do 1)
    valid_json_rate = round(total_valid_json / total_cases, 4) if total_cases > 0 else 0.0
    uplna_shoda_rate = round(total_uplna_shoda / total_cases, 4) if total_cases > 0 else 0.0
    avg_latency = round(total_latency / total_cases, 3) if total_cases > 0 else 0.0
    pole_rates = {k: round(v / total_cases, 4) for k, v in field_matches.items()}

    run_record = {
        "model": model,
        "poskytovatel": provider,
        "prompt": args.prompt,
        "sada": args.dataset,
        "pripadu": total_cases,
        "validni_json": valid_json_rate,
        "uplna_shoda": uplna_shoda_rate,
        "pole": pole_rates,
        "latence_s": avg_latency,
        "tokeny_vstup": total_prompt_tokens,
        "tokeny_vystup": total_completion_tokens,
    }

    # Uložení detailních surových odpovědí
    safe_model = re.sub(r"[^a-zA-Z0-9_.-]", "_", model)
    raw_file = RESULTS_DIR / f"{provider}_{safe_model}_{args.prompt}_{args.dataset}.json"
    with open(raw_file, "w", encoding="utf-8") as f:
        json.dump({
            "run": run_record,
            "cases": raw_results,
        }, f, ensure_ascii=False, indent=2)

    # Uložení do summary.json pro dashboard třídy
    summary_file = RESULTS_DIR / "summary.json"
    save_summary_result(summary_file, run_record)

    # Přehledný tisk výsledků
    print("\n" + "=" * 70)
    print("VÝSLEDKY EVALUACE:")
    print("=" * 70)
    print(f"Model / Poskytovatel : {model} ({provider})")
    print(f"Sada / Prompt        : {args.dataset} ({total_cases} případů) / {args.prompt}")
    print(f"Cache hity           : {cache_hits} z {total_cases}")
    print(f"Validní JSON         : {valid_json_rate * 100:.1f} % ({total_valid_json}/{total_cases})")
    print(f"Úplná shoda          : {uplna_shoda_rate * 100:.1f} % ({total_uplna_shoda}/{total_cases})")
    print("Přesnost po polích   :")
    for k, v in pole_rates.items():
        print(f"  - {k:<17}: {v * 100:.1f} %")
    print(f"Průměrná latence     : {avg_latency:.2f} s")
    print(f"Spotřeba tokenů      : Vstup = {total_prompt_tokens}, Výstup = {total_completion_tokens}")
    print(f"Surové výsledky      : {raw_file.relative_to(BASE_DIR)}")
    print(f"Aktualizován soubor  : {summary_file.relative_to(BASE_DIR)}")
    print("=" * 70)


if __name__ == "__main__":
    main()

