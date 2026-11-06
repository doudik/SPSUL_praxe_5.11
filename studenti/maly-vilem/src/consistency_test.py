#!/usr/bin/env python3
"""
Bonus: Test konzistence (temperature = 1.0).
Spustí 5 případů 5krát s temperature: 1.0 a vyhodnotí míru shody/variace.
"""

import json
import os
import sys
from eval import load_env, call_llm_api, parse_llm_json, normalize_str

def run_consistency_test(model="qwen/qwen3.8-27b", provider="groq", runs=5, cases_count=5):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_file = os.path.join(base_dir, ".env")
    env = load_env(env_file)
    api_key = env.get("GROQ_API_KEY")

    with open(os.path.join(base_dir, "prompts", "v1.txt"), "r", encoding="utf-8") as f:
        template = f.read()

    with open(os.path.join(base_dir, "data", "dev.jsonl"), "r", encoding="utf-8") as f:
        all_cases = [json.loads(line) for line in f if line.strip()][:cases_count]

    print(f"=== TEST KONZISTENCE (temperature=1.0) ===")
    print(f"Model: {model} | Případů: {len(all_cases)} | Opakování: {runs}")

    consistency_data = []

    for case in all_cases:
        cid = case["id"]
        inp = case["input"]
        prompt = template.replace("{input}", inp)

        outputs = []
        for r in range(runs):
            res = call_llm_api(provider, model, prompt, api_key, temperature=1.0)
            parsed = parse_llm_json(res.get("raw_output", ""))
            outputs.append(parsed)

        # Spočteme unikátní odpovědi
        unique_answers = []
        for o in outputs:
            o_norm = {k: normalize_str(v) for k, v in o.items()} if o else None
            if o_norm not in unique_answers:
                unique_answers.append(o_norm)

        is_stable = len(unique_answers) == 1
        print(f"ID {cid:02d}: {runs} běhů -> {len(unique_answers)} unikátní odpověď/i | Stabilní: {is_stable}")

        consistency_data.append({
            "id": cid,
            "input": inp,
            "expected": case["expected"],
            "runs_outputs": outputs,
            "unique_answers_count": len(unique_answers),
            "is_stable": is_stable
        })

    out_file = os.path.join(base_dir, "results", "consistency_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(consistency_data, f, ensure_ascii=False, indent=2)

    stable_count = sum(1 for c in consistency_data if c["is_stable"])
    print(f"Celkem stabilních: {stable_count}/{len(all_cases)} ({stable_count/len(all_cases)*100:.0f} %)")
    print(f"Uloženo do: {out_file}")

if __name__ == "__main__":
    run_consistency_test()

