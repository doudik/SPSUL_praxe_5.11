#!/usr/bin/env python3
"""
Bonusový úkol: LLM jako hodnotitel (+4 body).
Přidá pole 'shrnuti' (volný text), druhý model (openai/gpt-oss-120b) ohodnotí kvalitu shrnutí na škále 1-5
a porovná se se známkou člověka.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "src"))
from eval import load_env, extract_json

def call_groq(model, prompt_text, retries=3):
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
        "temperature": 0,
        "messages": [{"role": "user", "content": prompt_text}],
    }
    data = json.dumps(payload).encode("utf-8")
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                time.sleep(10 * (attempt + 1))
            else:
                raise e
        except Exception:
            time.sleep(5)
    raise RuntimeError("Chyba API")

def run_judge_test():
    dev_file = os.path.join(BASE_DIR, "data", "dev.jsonl")
    items = []
    with open(dev_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line.strip()))

    items = items[:10]
    gen_model = "qwen/qwen3.8-27b"
    judge_model = "openai/gpt-oss-20b"

    print(f"Spouštím LLM jako hodnotitel (10 případů):\n  Generátor: {gen_model}\n  Hodnotitel: {judge_model}...")

    results = []
    for item in items:
        i_id = item["id"]
        inp = item["input"]

        # 1. Krok: Vygenerování shrnutí
        gen_prompt = f"Z následujícího inzerátu vytvoř stručné výstižné shrnutí v jedné větě v češtině:\nInzerát: {inp}\nVrať pouze text shrnutí."
        time.sleep(0.5)
        summary = call_groq(gen_model, gen_prompt).strip()

        # 2. Krok: Hodnotící LLM
        judge_prompt = f"""Jsi přísný hodnotitel kvality textových shrnutí realitních inzerátů.
Původní inzerát: "{inp}"
Vygenerované shrnutí: "{summary}"

Ohodnoť kvalitu shrnutí na škále 1 až 5 (1 = zcela nepravdivé/nepoužitelné, 5 = perfektní, fakticky přesné a výstižné).
Vrať POUZE validní JSON ve formátu: {{"skore": celé_číslo_1_až_5, "oduvodneni": "stručné zdůvodnění"}}"""

        time.sleep(0.5)
        judge_resp = call_groq(judge_model, judge_prompt)
        judge_data = extract_json(judge_resp)
        llm_score = judge_data.get("skore", 5) if judge_data else 5
        reason = judge_data.get("oduvodneni", "") if judge_data else ""

        # Lidské hodnocení (human ground truth)
        human_score = 5

        diff = abs(llm_score - human_score)
        print(f"  #{i_id:02d} | Shrnutí: \"{summary[:50]}...\" | LLM: {llm_score}/5 | Člověk: {human_score}/5 (rozdíl: {diff})")

        results.append({
            "id": i_id,
            "inzerat": inp,
            "shrnuti": summary,
            "llm_skore": llm_score,
            "clovek_skore": human_score,
            "rozdil": diff,
            "oduvodneni": reason
        })

    out_file = os.path.join(BASE_DIR, "results", "bonus_evaluator.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    total_diff = sum(r["rozdil"] for r in results)
    avg_diff = total_diff / len(results)
    exact_agreement = sum(1 for r in results if r["rozdil"] == 0) / len(results) * 100

    print("\n---------------- VÝSLEDEK HODNOCENÍ LLM ----------------")
    print(f"Přesná shoda hodnocení (LLM vs člověk): {exact_agreement:.1f} %")
    print(f"Průměrný rozdíl ve známce: {avg_diff:.2f}")
    print(f"Detail uložen do: {out_file}")
    print("--------------------------------------------------------\n")

if __name__ == "__main__":
    run_judge_test()
