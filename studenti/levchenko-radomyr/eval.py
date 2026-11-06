import os
import json
import time
import hashlib
from dotenv import load_dotenv
from google import genai
from google.genai import errors

# Načtení proměnných z .env souboru
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

# Konfigurace běhu
MODEL_NAME = "gemini-3.5-flash-lite"
PROVIDER = "google"
PROMPT_VERSION = "v1"
DATASET_NAME = "dev"
DATASET_PATH = "data/dev.jsonl"
SUMMARY_PATH = "results/summary.json"
STUDENT_NAME = "Levchenko Radomyr"
TASK_NAME = "Jídelníček, alergeny"

os.makedirs("results", exist_ok=True)
os.makedirs("cache", exist_ok=True)

# Načtení promptu
with open(f"prompts/{PROMPT_VERSION}.txt", "r", encoding="utf-8") as f:
    system_prompt = f.read().strip()

# Načtení datasetu
with open(DATASET_PATH, "r", encoding="utf-8") as f:
    dataset = [json.loads(line) for line in f if line.strip()]

results_log = []
valid_json_count = 0
exact_match_count = 0
field_matches = {"nazev_jidla": 0, "kategorie": 0, "alergeny": 0}

total_prompt_tokens = 0
total_completion_tokens = 0
total_latency = 0.0

print(f"Spouštím vyhodnocení pro {len(dataset)} případů...")

for item in dataset:
    item_id = item["id"]
    user_input = item["input"]
    expected = item["expected"]

    # Mezipaměť (cache) podle klíče (model + prompt + vstup)
    cache_string = f"{MODEL_NAME}_{PROMPT_VERSION}_{user_input}"
    cache_hash = hashlib.md5(cache_string.encode("utf-8")).hexdigest()
    cache_file = os.path-join("cache", f"{cache_hash}.json") if hasattr(os.path, 'path') else f"cache/{cache_hash}.json"
    
    response_text = ""
    prompt_tokens = 0
    completion_tokens = 0
    latency = 0.0

    if os.path.exists(cache_file):
        # Načtení z cache
        with open(cache_file, "r", encoding="utf-8") as cf:
            cached_data = json.load(cf)
            response_text = cached_data["response_text"]
            prompt_tokens = cached_data["prompt_tokens"]
            completion_tokens = cached_data["completion_tokens"]
            latency = cached_data["latency"]
        print(f"[{item_id}/15] Načteno z cache.")
    else:
        # Volání API s ošetřením chyby 429 (Rate Limit)
        full_prompt = f"{system_prompt}\n\nVstup: {user_input}"
        success = False
        attempts = 0
        while not success and attempts < 5:
            try:
                start_time = time.time()
                response = client.models.generate_content(
			model=MODEL_NAME,
    			contents=full_prompt,
    			config={
        			"temperature": 0.0
    			}	
		)
                end_time = time.time()
                latency = end_time - start_time

                response_text = response.text
                usage = response.usage_metadata
                prompt_tokens = usage.prompt_token_count if usage else 0
                completion_tokens = usage.candidates_token_count if usage else 0

                success = True
            except errors.APIError as e:
                if "429" in str(e) or "ResourceExhausted" in str(e):
                    attempts += 1
                    wait_time = 15 * attempts
                    print(f"Limit vyčerpán (429). Čekám {wait_time} sekund před opakováním...")
                    time.sleep(wait_time)
                else:
                    raise e
            except Exception as e:
                attempts += 1
                time.sleep(5)

        # Uložení do cache
        if success:
            with open(cache_file, "w", encoding="utf-8") as cf:
                json.dump({
                    "response_text": response_text,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "latency": latency
                }, cf, ensure_ascii=False)
        print(f"[{item_id}/15] Zpracováno přes API.")

    total_prompt_tokens += prompt_tokens
    total_completion_tokens += completion_tokens
    total_latency += latency

    # 3. Zkouška parsování JSONu
    is_valid_json = False
    parsed_output = {}
    try:
        # Oříznutí případných markdown značek
        clean_text = response_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        parsed_output = json.loads(clean_text)
        is_valid_json = True
        valid_json_count += 1
    except json.JSONDecodeError:
        parsed_output = None

    # 4. Porovnání se správnou odpovědí (expected)
    match_nazev = False
    match_kategorie = False
    match_alergeny = False

    if is_valid_json and isinstance(parsed_output, dict):
        if str(parsed_output.get("nazev_jidla", "")).strip().lower() == str(expected.get("nazev_jidla", "")).strip().lower():
            match_nazev = True
            field_matches["nazev_jidla"] += 1
            
        if str(parsed_output.get("kategorie", "")).strip().lower() == str(expected.get("kategorie", "")).strip().lower():
            match_kategorie = True
            field_matches["kategorie"] += 1

        # Porovnání polí alergenů (ignorujeme pořadí čísel)
        exp_alg = sorted(list(expected.get("alergeny", [])))
        out_alg = sorted(list(parsed_output.get("alergeny", [])))
        if exp_alg == out_alg:
            match_alergeny = True
            field_matches["alergeny"] += 1

    is_exact_match = match_nazev and match_kategorie and match_alergeny
    if is_exact_match:
        exact_match_count += 1

    results_log.append({
        "id": item_id,
        "input": user_input,
        "expected": expected,
        "raw_response": response_text,
        "parsed": parsed_output,
        "valid_json": is_valid_json,
        "exact_match": is_exact_match
    })

# Výpočet celkových metrik
n = len(dataset)
metrics = {
    "student": STUDENT_NAME,
    "uloha": TASK_NAME,
    "behy": [
        {
            "model": MODEL_NAME,
            "poskytovatel": PROVIDER,
            "prompt": PROMPT_VERSION,
            "sada": DATASET_NAME,
            "pripadu": n,
            "validni_json": round(valid_json_count / n, 2),
            "uplna_shoda": round(exact_match_count / n, 2),
            "pole": {
                "nazev_jidla": round(field_matches["nazev_jidla"] / n, 2),
                "kategorie": round(field_matches["kategorie"] / n, 2),
                "alergeny": round(field_matches["alergeny"] / n, 2)
            },
            "latence_s": round(total_latency / n, 2),
            "tokeny_vstup": total_prompt_tokens,
            "tokeny_vystup": total_completion_tokens
        }
    ]
}

# 8. Uložení výsledku (pokud už soubor existuje, přepíše se podle pravidel)
with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
    json.dump(metrics, f, ensure_ascii=False, indent=2)

print("\n=== VYHODNOCENÍ DOKONČENO ===")
print(f"Výsledky uloženy do {SUMMARY_PATH}")
print(json.dumps(metrics, ensure_ascii=False, indent=2))