#!/usr/bin/env python3
"""
Bonusový úkol: Měření konzistence výstupů LLM s temperature: 1 (+3 body).
Pustí 5 vybraných případů 5krát za sebou a vyhodnotí míru variability odpovědí.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
from eval import load_env, extract_json, evaluate_prediction

def call_llm_temp1(model, prompt_text, retries=3):
    load_env()
    api_key = os.getenv("GROQ_API_KEY")
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    payload = {
        "model": model,
        "temperature": 1.0,
        "messages": [{"role": "user", "content": prompt_text}],
    }
    data = json.dumps(payload).encode("utf-8")
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                time.sleep(10 * (attempt + 1))
            else:
                raise e
    raise RuntimeError("Chyba volání API.")

def run_consistency_test():
    prompt_file = os.path.join(BASE_DIR, "prompts", "v1.txt")
    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt_tmpl = f.read()

    dev_file = os.path.join(BASE_DIR, "data", "dev.jsonl")
    items = []
    with open(dev_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line.strip()))

    test_items = items[:5]
    model = "qwen/qwen3.8-27b"
    runs_per_item = 5

    print(f"Spouštím test konzistence (5 inzerátů, 5 běhů každý, temperature=1.0) na modelu {model}...")

    results = []
    for item in test_items:
        i_id = item["id"]
        exp = item["expected"]
        inp = item["input"]
        prompt = prompt_tmpl.replace("{input}", inp)

        run_answers = []
        for r_idx in range(runs_per_item):
            time.sleep(0.5)
            ans = call_llm_temp1(model, prompt)
            pred = extract_json(ans)
            eval_res = evaluate_prediction(pred, exp)
            run_answers.append({
                "run": r_idx + 1,
                "pred": pred,
                "match": eval_res["uplna_shoda"]
            })

        # Zjištění, zda jsou všechny predikce identické
        first_pred = run_answers[0]["pred"]
        identical_count = sum(1 for a in run_answers if a["pred"] == first_pred)
        matches_count = sum(1 for a in run_answers if a["match"])

        results.append({
            "id": i_id,
            "identical_pct": (identical_count / runs_per_item) * 100,
            "accuracy_pct": (matches_count / runs_per_item) * 100,
            "answers": [a["pred"] for a in run_answers]
        })
        print(f"  Případ ID {i_id}: shoda odpovědí {identical_count}/{runs_per_item}, přesnost {matches_count}/{runs_per_item}")

    out_file = os.path.join(BASE_DIR, "results", "bonus_consistency.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    avg_identical = sum(r["identical_pct"] for r in results) / len(results)
    avg_accuracy = sum(r["accuracy_pct"] for r in results) / len(results)

    print("\n---------------- VÝSLEDEK TESTU KONZISTENCE ----------------")
    print(f"Průměrná identičnost odpovědí: {avg_identical:.1f} %")
    print(f"Průměrná přesnost vůči ground truth: {avg_accuracy:.1f} %")
    print(f"Uloženo do: {out_file}")
    print("-----------------------------------------------------------\n")

if __name__ == "__main__":
    run_consistency_test()
