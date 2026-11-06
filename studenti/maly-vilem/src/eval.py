#!/usr/bin/env python3
"""
Evaluační skript pro hlášení závad v učebně.
Měří úspěšnost extrakce strukturovaných dat z hlášení pomocí LLM.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error

# Poskytovatelé a výchozí URL
PROVIDERS = {
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "env_key": "GROQ_API_KEY",
    },
    "nvidia": {
        "url": "https://integrate.api.nvidia.com/v1/chat/completions",
        "env_key": "NVIDIA_API_KEY",
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "env_key": "GEMINI_API_KEY",
    },
    "mistral": {
        "url": "https://api.mistral.ai/v1/chat/completions",
        "env_key": "MISTRAL_API_KEY",
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "env_key": "OPENROUTER_API_KEY",
    },
}


def load_env(env_path):
    """Načte proměnné prostředí ze zadaného souboru .env."""
    env = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip("'\"")
    return env


def normalize_str(val):
    """Normalizuje textovou hodnotu: trim a sjednocení vícenásobných mezer."""
    if val is None:
        return None
    val = str(val).strip().lower()
    val = re.sub(r"\s+", " ", val)
    return val


def parse_llm_json(raw_text):
    """
    Bezpečně rozparsuje odpověď LLM jako JSON.
    Podporuje odpovědi obalené v markdownu (```json ... ```).
    """
    if not raw_text or not isinstance(raw_text, str):
        return None

    cleaned = raw_text.strip()
    # Odstranění markdown bloků ```json ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if match:
        cleaned = match.group(1).strip()
    else:
        # Zkusíme najít první '{' a poslední '}'
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start : end + 1]

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return None


def compare_field(field_name, expected_val, predicted_val):
    """
    Porovná jedno pole podle pravidel z Fáze 1:
    - kategorie & priorita: malá/velká písmena nevadí, mezery se trimují
    - ucebna: text po sjednocení mezer a lowercase, null musí být null
    """
    if expected_val is None:
        # Očekáváme null / None
        return predicted_val is None or str(predicted_val).strip().lower() in ("null", "none", "")

    if predicted_val is None:
        return False

    norm_exp = normalize_str(expected_val)
    norm_pred = normalize_str(predicted_val)

    return norm_exp == norm_pred


def call_llm_api(provider_name, model_name, prompt_text, api_key, temperature=0, max_retries=5, retry_delay=12):
    """
    Zavolá OpenAI-kompatibilní API pro chat completions.
    Obsahuje retry logiku při 429 rate limitu.
    """
    if provider_name not in PROVIDERS:
        raise ValueError(f"Neznámý poskytovatel: {provider_name}")

    provider_info = PROVIDERS[provider_name]
    url = provider_info["url"]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "EvaluationScript/1.0",
    }

    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": prompt_text}
        ],
        "temperature": temperature,
    }

    data_bytes = json.dumps(payload).encode("utf-8")

    for attempt in range(1, max_retries + 1):
        try:
            t0 = time.time()
            req = urllib.request.Request(url, headers=headers, data=data_bytes)
            with urllib.request.urlopen(req, timeout=40) as response:
                latency = round(time.time() - t0, 3)
                resp_json = json.loads(response.read().decode("utf-8"))

                choice = resp_json.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                usage = resp_json.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)

                return {
                    "raw_output": content,
                    "latency_s": latency,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "error": None,
                }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            if e.code == 429:
                wait_time = retry_delay * attempt
                print(f"  [HTTP 429 Rate Limit] Čekám {wait_time} s (pokus {attempt}/{max_retries})...")
                time.sleep(wait_time)
                continue
            elif e.code in (500, 502, 503, 504):
                wait_time = 5 * attempt
                print(f"  [HTTP {e.code} Server Error] Čekám {wait_time} s...")
                time.sleep(wait_time)
                continue
            else:
                return {
                    "raw_output": "",
                    "latency_s": 0.0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "error": f"HTTP {e.code}: {err_body}",
                }
        except Exception as e:
            return {
                "raw_output": "",
                "latency_s": 0.0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "error": str(e),
            }

    return {
        "raw_output": "",
        "latency_s": 0.0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "error": "Vyčerpán maximální počet pokusů při Rate Limitu (429)",
    }


def get_cache_key(model, prompt_name, input_text):
    """Vypočítá hash klíč pro mezipaměť."""
    unique_str = f"{model}___{prompt_name}___{input_text.strip()}"
    return hashlib.sha256(unique_str.encode("utf-8")).hexdigest()


def evaluate(
    model,
    provider,
    prompt_name="v1",
    dataset_name="dev",
    base_dir=".",
    use_cache=True,
    delay=0.5,
    student_name="Vilém Malý",
    task_name="Hlášení závad v učebně",
):
    """Hlavní evaluační funkce."""
    # Cesty k souborům
    env_file = os.path.join(base_dir, ".env")
    prompts_dir = os.path.join(base_dir, "prompts")
    data_dir = os.path.join(base_dir, "data")
    cache_dir = os.path.join(base_dir, "cache")
    results_dir = os.path.join(base_dir, "results")

    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    # Načtení klíče
    env = load_env(env_file)
    # Případně fallback na os.environ
    for k, v in os.environ.items():
        if k not in env:
            env[k] = v

    provider_info = PROVIDERS.get(provider.lower())
    if not provider_info:
        raise ValueError(f"Poskytovatel '{provider}' není podporován. Možnosti: {list(PROVIDERS.keys())}")

    env_var_name = provider_info["env_key"]
    api_key = env.get(env_var_name)
    if not api_key:
        raise ValueError(f"Chybí API klíč {env_var_name} v souboru {env_file} nebo systémových proměnných.")

    # Načtení prompt šablony
    prompt_file = os.path.join(prompts_dir, f"{prompt_name}.txt")
    if not os.path.exists(prompt_file):
        raise FileNotFoundError(f"Soubor s promptem {prompt_file} nebyl nalezen.")

    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    # Načtení datasetu
    dataset_file = os.path.join(data_dir, f"{dataset_name}.jsonl")
    if not os.path.exists(dataset_file):
        raise FileNotFoundError(f"Soubor s daty {dataset_file} nebyl nalezen.")

    cases = []
    with open(dataset_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))

    print(f"=== SPUŠTĚNÍ EVALUACE ===")
    print(f"Model: {model} ({provider})")
    print(f"Prompt: {prompt_name} | Sada: {dataset_name} ({len(cases)} případů)")
    print(f"Cache aktivní: {use_cache}")
    print("--------------------------------------------------")

    results_details = []
    total_valid_json = 0
    total_exact_match = 0
    field_matches = {"kategorie": 0, "priorita": 0, "ucebna": 0}
    total_tokens_in = 0
    total_tokens_out = 0
    latencies = []

    for idx, case in enumerate(cases, start=1):
        case_id = case.get("id", idx)
        input_text = case.get("input", "")
        expected = case.get("expected", {})
        tezky = case.get("tezky", False)

        # Doplnění vstupu do šablony
        if "{input}" in prompt_template:
            full_prompt = prompt_template.replace("{input}", input_text)
        else:
            full_prompt = f"{prompt_template}\n\nText hlášení:\n{input_text}"

        cache_key = get_cache_key(model, prompt_name, input_text)
        cache_file = os.path.join(cache_dir, f"{cache_key}.json")

        call_res = None
        from_cache = False

        if use_cache and os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as cf:
                    call_res = json.load(cf)
                    from_cache = True
            except Exception:
                pass

        if not call_res:
            call_res = call_llm_api(provider, model, full_prompt, api_key)
            if use_cache and not call_res.get("error"):
                with open(cache_file, "w", encoding="utf-8") as cf:
                    json.dump(call_res, cf, ensure_ascii=False, indent=2)
            if delay > 0:
                time.sleep(delay)

        raw_output = call_res.get("raw_output", "")
        latency = call_res.get("latency_s", 0.0)
        p_tokens = call_res.get("prompt_tokens", 0)
        c_tokens = call_res.get("completion_tokens", 0)

        total_tokens_in += p_tokens
        total_tokens_out += c_tokens
        latencies.append(latency)

        parsed_json = parse_llm_json(raw_output)
        is_valid = parsed_json is not None

        case_field_match = {}
        all_fields_match = False

        if is_valid:
            total_valid_json += 1
            cat_ok = compare_field("kategorie", expected.get("kategorie"), parsed_json.get("kategorie"))
            prio_ok = compare_field("priorita", expected.get("priorita"), parsed_json.get("priorita"))
            room_ok = compare_field("ucebna", expected.get("ucebna"), parsed_json.get("ucebna"))

            case_field_match = {"kategorie": cat_ok, "priorita": prio_ok, "ucebna": room_ok}

            if cat_ok:
                field_matches["kategorie"] += 1
            if prio_ok:
                field_matches["priorita"] += 1
            if room_ok:
                field_matches["ucebna"] += 1

            if cat_ok and prio_ok and room_ok:
                total_exact_match += 1
                all_fields_match = True
        else:
            case_field_match = {"kategorie": False, "priorita": False, "ucebna": False}

        tag = "CACHE" if from_cache else "API"
        status_sym = "✅" if all_fields_match else ("⚠️" if is_valid else "❌")
        print(f"[{idx:02d}/{len(cases):02d}] {status_sym} id={case_id} ({tag}) lat={latency:.2f}s | JSON: {is_valid} | Shoda: {all_fields_match}")
        if not all_fields_match:
            print(f"       Exp : {expected}")
            print(f"       Got : {parsed_json if is_valid else raw_output[:80]}")

        results_details.append({
            "id": case_id,
            "tezky": tezky,
            "input": input_text,
            "expected": expected,
            "predicted_raw": raw_output,
            "predicted_json": parsed_json,
            "valid_json": is_valid,
            "exact_match": all_fields_match,
            "field_matches": case_field_match,
            "latency_s": latency,
            "tokens_in": p_tokens,
            "tokens_out": c_tokens,
            "from_cache": from_cache,
            "error": call_res.get("error"),
        })

    n = len(cases)
    valid_json_ratio = round(total_valid_json / n, 4) if n > 0 else 0.0
    exact_match_ratio = round(total_exact_match / n, 4) if n > 0 else 0.0
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

    field_ratios = {
        k: round(v / n, 4) if n > 0 else 0.0
        for k, v in field_matches.items()
    }

    # Uložení surových výsledků běhu
    safe_model_name = re.sub(r"[^\w\-.]", "_", model)
    run_file_name = f"{safe_model_name}_{provider}_{prompt_name}_{dataset_name}.json"
    run_file_path = os.path.join(results_dir, run_file_name)
    with open(run_file_path, "w", encoding="utf-8") as rf:
        json.dump({
            "model": model,
            "provider": provider,
            "prompt": prompt_name,
            "dataset": dataset_name,
            "cases_count": n,
            "metrics": {
                "valid_json": valid_json_ratio,
                "exact_match": exact_match_ratio,
                "fields": field_ratios,
                "avg_latency_s": avg_latency,
                "total_tokens_in": total_tokens_in,
                "total_tokens_out": total_tokens_out,
            },
            "details": results_details,
        }, rf, ensure_ascii=False, indent=2)

    # Zápis / aktualizace results/summary.json
    summary_path = os.path.join(results_dir, "summary.json")
    summary_data = {
        "student": student_name,
        "uloha": task_name,
        "behy": [],
    }

    if os.path.exists(summary_path):
        try:
            with open(summary_path, "r", encoding="utf-8") as sf:
                existing = json.load(sf)
                if isinstance(existing, dict):
                    summary_data["student"] = existing.get("student", student_name)
                    summary_data["uloha"] = existing.get("uloha", task_name)
                    summary_data["behy"] = existing.get("behy", [])
        except Exception:
            pass

    new_beh_record = {
        "model": model,
        "poskytovatel": provider.lower(),
        "prompt": prompt_name,
        "sada": dataset_name,
        "pripadu": n,
        "validni_json": valid_json_ratio,
        "uplna_shoda": exact_match_ratio,
        "pole": field_ratios,
        "latence_s": avg_latency,
        "tokeny_vstup": total_tokens_in,
        "tokeny_vystup": total_tokens_out,
    }

    # Přepíše existující záznam se stejným (model, poskytovatel, prompt, sada)
    updated = False
    for i, b in enumerate(summary_data["behy"]):
        if (
            b.get("model") == model
            and b.get("poskytovatel") == provider.lower()
            and b.get("prompt") == prompt_name
            and b.get("sada") == dataset_name
        ):
            summary_data["behy"][i] = new_beh_record
            updated = True
            break

    if not updated:
        summary_data["behy"].append(new_beh_record)

    with open(summary_path, "w", encoding="utf-8") as sf:
        json.dump(summary_data, sf, ensure_ascii=False, indent=2)

    print("\n--------------------------------------------------")
    print(f"=== VÝSLEDKY BĚHU ===")
    print(f"Validní JSON:  {valid_json_ratio * 100:.1f} %")
    print(f"Úplná shoda:   {exact_match_ratio * 100:.1f} %")
    print(f"Pole:          {field_ratios}")
    print(f"Prům. latence: {avg_latency:.2f} s")
    print(f"Tokeny:        vstup={total_tokens_in}, výstup={total_tokens_out}")
    print(f"Uloženo do:    {summary_path} a {run_file_path}")
    print("==================================================\n")

    return new_beh_record


def main():
    parser = argparse.ArgumentParser(description="Evaluační skript pro hlášení závad.")
    parser.add_argument("--model", type=str, default="openai/gpt-oss-20b", help="Název LLM modelu.")
    parser.add_argument("--provider", type=str, default="groq", choices=list(PROVIDERS.keys()), help="Poskytovatel API.")
    parser.add_argument("--prompt", type=str, default="v1", help="Název promptu (v1, v2).")
    parser.add_argument("--dataset", type=str, default="dev", choices=["dev", "test"], help="Sada (dev, test).")
    parser.add_argument("--no-cache", action="store_true", help="Vypne použití mezipaměti.")
    parser.add_argument("--delay", type=float, default=0.5, help="Pauza mezi požadavky v sekundách.")
    parser.add_argument("--base-dir", type=str, default=None, help="Základní složka studenta (výchozí: detekce složky skriptu).")

    args = parser.parse_args()

    # Automatická detekce základní složky studenta
    if args.base_dir:
        base_dir = args.base_dir
    else:
        # Skript je v src/, složka studenta je o úroveň výš
        script_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(script_dir)

    evaluate(
        model=args.model,
        provider=args.provider,
        prompt_name=args.prompt,
        dataset_name=args.dataset,
        base_dir=base_dir,
        use_cache=not args.no_cache,
        delay=args.delay,
    )


if __name__ == "__main__":
    main()

