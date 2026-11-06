#!/usr/bin/env python3
"""
Evaluační skript pro měření úspěšnosti LLM při extrakci dat z inzerátů bytů.
Podporuje Groq, Mistral, Google (Gemini) a OpenRouter.
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

# Cesty k adresářům projektu
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
CACHE_DIR = os.path.join(BASE_DIR, "cache")

PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "env_var": "GROQ_API_KEY",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "env_var": "GEMINI_API_KEY",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1/chat/completions",
        "env_var": "MISTRAL_API_KEY",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "env_var": "OPENROUTER_API_KEY",
    },
}


def load_env():
    """Načte proměnné prostředí ze souboru .env."""
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def get_cache_path(provider, model, prompt_name, input_text):
    """Vrátí cestu k souboru v mezipaměti na základě hashe."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    raw_key = f"{provider}:{model}:{prompt_name}:{input_text}"
    key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, f"{key_hash}.json")


def call_llm(provider, model, prompt_text, retries=3):
    """
    Zavolá API poskytovatele s teplotou 0 a ošetřením rate limitů (429/503).
    """
    prov_config = PROVIDERS.get(provider.lower())
    if not prov_config:
        raise ValueError(f"Neznámý poskytovatel: {provider}")

    api_key = os.getenv(prov_config["env_var"])
    if not api_key:
        raise ValueError(f"Chybí API klíč v proměnné {prov_config['env_var']}. Zkontroluj .env soubor.")

    url = prov_config["base_url"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "user", "content": prompt_text}
        ],
    }

    data = json.dumps(payload).encode("utf-8")

    for attempt in range(retries):
        try:
            start_time = time.time()
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                latency = round(time.time() - start_time, 3)
                body = json.loads(resp.read().decode("utf-8"))

            choice = body["choices"][0]["message"]["content"]
            usage = body.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)

            return {
                "content": choice,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "latency_s": latency,
            }

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            if e.code in (429, 503):
                wait_time = (attempt + 1) * 10
                print(f"  [HTTP {e.code}] Rate limit nebo přetížení, čekám {wait_time} s (pokus {attempt + 1}/{retries})...")
                time.sleep(wait_time)
            else:
                print(f"  [Chyba HTTP {e.code}]: {err_body}")
                raise e
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(5)
            else:
                raise e

    raise RuntimeError("Překročen maximální počet pokusů při volání API.")


def extract_json(raw_text):
    """Pokusí se extrahovat a naparsovat JSON z textové odpovědi modelu."""
    if not raw_text:
        return None

    text = raw_text.strip()

    # Ořezání markdown kódových bloků (```json ... ```)
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1).strip()

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # Fallback: nalezení prvního '{' a posledního '}'
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            data = json.loads(text[first_brace:last_brace + 1])
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    return None


def normalize_str(val):
    """Normalizuje řetězec pro porovnání (malá písmena, bez bílých znaků)."""
    if val is None:
        return None
    return str(val).strip().lower()


def evaluate_prediction(pred, exp):
    """
    Porovná predikci modelu se správnou odpovědí (ground truth)
    podle pravidel v README.md.
    """
    if not isinstance(pred, dict):
        return {
            "dispozice": False,
            "plocha_m2": False,
            "cena_kc": False,
            "mesto": False,
            "uplna_shoda": False,
        }

    # 1. Dispozice (case-insensitive shoda bez mezer)
    p_disp = normalize_str(pred.get("dispozice"))
    e_disp = normalize_str(exp.get("dispozice"))
    if p_disp:
        p_disp = p_disp.replace(" ", "")
    if e_disp:
        e_disp = e_disp.replace(" ", "")
    disp_ok = (p_disp == e_disp)

    # 2. Plocha m2 (číselná shoda)
    p_area = pred.get("plocha_m2")
    e_area = exp.get("plocha_m2")
    try:
        p_area_val = int(p_area) if p_area is not None else None
    except (ValueError, TypeError):
        p_area_val = "INVALID"
    area_ok = (p_area_val == e_area)

    # 3. Cena v Kč (číselná shoda)
    p_price = pred.get("cena_kc")
    e_price = exp.get("cena_kc")
    try:
        p_price_val = int(p_price) if p_price is not None else None
    except (ValueError, TypeError):
        p_price_val = "INVALID"
    price_ok = (p_price_val == e_price)

    # 4. Město (case-insensitive shoda řetězce po ořezu)
    p_city = normalize_str(pred.get("mesto"))
    e_city = normalize_str(exp.get("mesto"))
    city_ok = (p_city == e_city)

    all_ok = disp_ok and area_ok and price_ok and city_ok

    return {
        "dispozice": disp_ok,
        "plocha_m2": area_ok,
        "cena_kc": price_ok,
        "mesto": city_ok,
        "uplna_shoda": all_ok,
    }


def update_summary_json(run_record):
    """
    Uloží běh do results/summary.json. Pokud stejný běh již existuje, přepíše ho.
    Formát striktně odpovídá požadavkům pro školní dashboard.
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)
    summary_path = os.path.join(RESULTS_DIR, "summary.json")

    data = {
        "student": "Jiří Podolský",
        "uloha": "Inzeráty bytů",
        "behy": []
    }

    if os.path.exists(summary_path):
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict) and "behy" in loaded:
                    data = loaded
        except Exception:
            pass

    # Nahrazení existujícího běhu se stejnými parametry nebo přidání nového
    new_behy = []
    replaced = False
    for b in data.get("behy", []):
        if (b.get("model") == run_record["model"] and
            b.get("poskytovatel") == run_record["poskytovatel"] and
            b.get("prompt") == run_record["prompt"] and
            b.get("sada") == run_record["sada"]):
            new_behy.append(run_record)
            replaced = True
        else:
            new_behy.append(b)

    if not replaced:
        new_behy.append(run_record)

    data["behy"] = new_behy

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Výsledky uloženy do: {summary_path}")


def run_evaluation(provider, model, prompt_name, dataset_name):
    """Spustí kompletní evaluaci na vybrané sadě."""
    load_env()

    # Načtení promptu
    prompt_file = os.path.join(PROMPTS_DIR, f"{prompt_name}.txt")
    if not os.path.exists(prompt_file):
        raise FileNotFoundError(f"Soubor s promptem neexistuje: {prompt_file}")
    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    # Načtení datasetu
    dataset_file = os.path.join(DATA_DIR, f"{dataset_name}.jsonl")
    if not os.path.exists(dataset_file):
        raise FileNotFoundError(f"Soubor s daty neexistuje: {dataset_file}")

    items = []
    with open(dataset_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))

    total_count = len(items)
    print(f"\n=======================================================")
    print(f"Spouštím evaluaci: {provider} | {model}")
    print(f"Prompt: {prompt_name} | Sada: {dataset_name} ({total_count} případů)")
    print(f"=======================================================\n")

    valid_json_count = 0
    all_match_count = 0
    field_matches = {"dispozice": 0, "plocha_m2": 0, "cena_kc": 0, "mesto": 0}
    total_latency = 0.0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    raw_results = []

    for idx, item in enumerate(items, 1):
        item_id = item["id"]
        input_text = item["input"]
        expected = item["expected"]

        full_prompt = prompt_template.replace("{input}", input_text)

        # Kontrola cache
        cache_file = get_cache_path(provider, model, prompt_name, input_text)
        from_cache = False

        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                llm_res = json.load(f)
                from_cache = True
        else:
            # Krátká pauza pro ochranu rate limitu (zejména Groq / 8k token/min)
            time.sleep(0.5)
            llm_res = call_llm(provider, model, full_prompt)
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(llm_res, f, ensure_ascii=False, indent=2)

        raw_output = llm_res["content"]
        total_latency += llm_res.get("latency_s", 0.0)
        total_prompt_tokens += llm_res.get("prompt_tokens", 0)
        total_completion_tokens += llm_res.get("completion_tokens", 0)

        # Parsování JSONu
        pred = extract_json(raw_output)
        is_valid = pred is not None
        if is_valid:
            valid_json_count += 1

        eval_res = evaluate_prediction(pred, expected)
        if eval_res["uplna_shoda"]:
            all_match_count += 1

        for field in field_matches:
            if eval_res[field]:
                field_matches[field] += 1

        cache_str = "[CACHE]" if from_cache else "[API]  "
        status_sym = "OK" if eval_res["uplna_shoda"] else ("JSON" if is_valid else "ERR")
        print(f"  {cache_str} #{idx:02d} (ID {item_id:3d}) | {status_sym:4s} | "
              f"Disp: {'✓' if eval_res['dispozice'] else '✗'} | "
              f"Plocha: {'✓' if eval_res['plocha_m2'] else '✗'} | "
              f"Cena: {'✓' if eval_res['cena_kc'] else '✗'} | "
              f"Město: {'✓' if eval_res['mesto'] else '✗'}")

        raw_results.append({
            "id": item_id,
            "input": input_text,
            "expected": expected,
            "raw_output": raw_output,
            "prediction": pred,
            "evaluation": eval_res,
        })

    # Výpočet konečných metrik (zaokrouhleno na 2-3 desetinná místa)
    valid_json_ratio = round(valid_json_count / total_count, 3)
    all_match_ratio = round(all_match_count / total_count, 3)
    fields_ratio = {k: round(v / total_count, 3) for k, v in field_matches.items()}
    avg_latency = round(total_latency / total_count, 2)

    # Uložení detailních surových výsledků běhu
    os.makedirs(RESULTS_DIR, exist_ok=True)
    clean_model_name = model.replace("/", "_").replace(":", "_")
    detail_filename = f"{provider}_{clean_model_name}_{prompt_name}_{dataset_name}.json"
    detail_path = os.path.join(RESULTS_DIR, detail_filename)
    with open(detail_path, "w", encoding="utf-8") as f:
        json.dump(raw_results, f, ensure_ascii=False, indent=2)

    # Záznam pro summary.json (striktně dle specifikace)
    run_record = {
        "model": model,
        "poskytovatel": provider.lower(),
        "prompt": prompt_name,
        "sada": dataset_name,
        "pripadu": total_count,
        "validni_json": valid_json_ratio,
        "uplna_shoda": all_match_ratio,
        "pole": fields_ratio,
        "latence_s": avg_latency,
        "tokeny_vstup": total_prompt_tokens,
        "tokeny_vystup": total_completion_tokens,
    }

    update_summary_json(run_record)

    # Výpis souhrnu
    print("\n------------------- SOUHRN BĚHU -------------------")
    print(f"Model: {model} ({provider}) | Prompt: {prompt_name} | Sada: {dataset_name}")
    print(f"Validní JSON:     {valid_json_ratio * 100:.1f} %")
    print(f"Úplná shoda:      {all_match_ratio * 100:.1f} %")
    print(f"Přesnost polí:")
    for k, v in fields_ratio.items():
        print(f"  - {k:10s}: {v * 100:.1f} %")
    print(f"Průměrná latence: {avg_latency} s")
    print(f"Tokeny:           vstup: {total_prompt_tokens} | výstup: {total_completion_tokens}")
    print(f"Detailní log:     {detail_path}")
    print("---------------------------------------------------\n")

    return run_record


def main():
    parser = argparse.ArgumentParser(description="Evaluační skript pro inzeráty bytů.")
    parser.add_argument("--provider", default="groq", choices=["groq", "gemini", "mistral", "openrouter"],
                        help="Poskytovatel API (výchozí: groq)")
    parser.add_argument("--model", default="openai/gpt-oss-20b",
                        help="Název modelu (výchozí: openai/gpt-oss-20b)")
    parser.add_argument("--prompt", default="v1", help="Název promptu (v1, v2; výchozí: v1)")
    parser.add_argument("--dataset", default="dev", choices=["dev", "test"],
                        help="Datová sada (dev nebo test; výchozí: dev)")

    args = parser.parse_args()
    run_evaluation(args.provider, args.model, args.prompt, args.dataset)


if __name__ == "__main__":
    main()
