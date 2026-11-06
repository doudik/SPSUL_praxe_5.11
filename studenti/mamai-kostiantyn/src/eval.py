"""Evaluate an OpenAI-compatible chat model on the SMS classification dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
        "default_model": "openai/gpt-oss-20b",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key_env": "OPENROUTER_API_KEY",
        "default_model": "google/gemma-3-27b-it:free",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "key_env": "GEMINI_API_KEY",
        "default_model": "gemini-2.5-flash",
    },
}

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "cache"
RESULTS_DIR = ROOT / "results"


def load_dotenv() -> None:
    """Load simple KEY=value entries from the student's .env file."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        os.environ.setdefault(key, value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=sorted(PROVIDERS), required=True)
    parser.add_argument("--model", help="Model name; defaults to the provider's default.")
    parser.add_argument("--set", choices=("dev", "test"), default="dev")
    parser.add_argument("--prompt", choices=("v1", "v2"), default="v1")
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--retry-delay", type=float, default=10.0)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not raw_line.strip():
            continue
        try:
            item = json.loads(raw_line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {error}") from error
        if not isinstance(item, dict):
            raise ValueError(f"{path}:{line_number}: expected a JSON object")
        for field in ("id", "input", "expected"):
            if field not in item:
                raise ValueError(f"{path}:{line_number}: missing field '{field}'")
        cases.append(item)
    if not cases:
        raise ValueError(f"{path}: dataset is empty")
    return cases


def load_prompt(path: Path) -> str:
    prompt = path.read_text(encoding="utf-8").strip()
    if not prompt:
        raise ValueError(f"{path}: prompt is empty")
    return prompt


def cache_key(model: str, prompt: str, text: str) -> str:
    payload = json.dumps(
        {"model": model, "prompt": prompt, "input": text},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def extract_message_content(response: dict[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("API response has no choices")
    message = choices[0].get("message", {})
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [part.get("text", "") for part in content if isinstance(part, dict)]
        return "".join(parts)
    raise ValueError("API response has no text content")


def request_model(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    text: str,
    max_retries: int,
    retry_delay: float,
) -> tuple[str, dict[str, Any], float]:
    url = f"{base_url.rstrip('/')}/chat/completions"
    body = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
    }
    request = Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    for attempt in range(max_retries + 1):
        started = time.perf_counter()
        try:
            with urlopen(request, timeout=120) as response:
                raw_response = json.loads(response.read().decode("utf-8"))
            latency = time.perf_counter() - started
            return extract_message_content(raw_response), raw_response, latency
        except HTTPError as error:
            if error.code != 429 or attempt >= max_retries:
                details = error.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"API HTTP {error.code}: {details[:500]}") from error
            retry_after = error.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else retry_delay * (attempt + 1)
            print(f"Rate limit (429), ÄekÃ¡m {delay:g} s...", file=sys.stderr)
            time.sleep(delay)
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            if attempt >= max_retries:
                raise RuntimeError(f"API request failed: {error}") from error
            delay = retry_delay * (attempt + 1)
            print(f"Chyba spojenÃ­, opakuji za {delay:g} s...", file=sys.stderr)
            time.sleep(delay)
    raise RuntimeError("Request retry loop ended unexpectedly")


def parse_model_json(raw_text: str) -> dict[str, Any] | None:
    cleaned = raw_text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def normalize(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    without_accents = "".join(
        character
        for character in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(character)
    )
    return " ".join(without_accents.casefold().split())


def values_equal(actual: Any, expected: Any) -> bool:
    return normalize(actual) == normalize(expected)


def result_path(provider: str, model: str, prompt_name: str, dataset_name: str) -> Path:
    safe_model = re.sub(r"[^A-Za-z0-9._-]+", "_", model)
    return RESULTS_DIR / f"{provider}_{safe_model}_{prompt_name}_{dataset_name}.json"


def main() -> int:
    load_dotenv()
    args = parse_args()
    provider = PROVIDERS[args.provider]
    model = args.model or provider["default_model"]
    api_key = os.getenv(provider["key_env"])
    if not api_key:
        raise SystemExit(
            f"ChybÃ­ {provider['key_env']}. PÅ™idej ho do "
            f"{ROOT / '.env'} nebo nastav jako promÄ›nnou prostÅ™edÃ­."
        )

    dataset_path = ROOT / "data" / f"{args.set}.jsonl"
    prompt_path = ROOT / "prompts" / f"{args.prompt}.txt"
    cases = read_jsonl(dataset_path)
    prompt = load_prompt(prompt_path)
    CACHE_DIR.mkdir(exist_ok=True)
    RESULTS_DIR.mkdir(exist_ok=True)

    fields = ("phishing", "typ_podvodu")
    records: list[dict[str, Any]] = []
    field_matches = {field: 0 for field in fields}
    valid_count = 0
    complete_matches = 0
    total_latency = 0.0
    input_tokens = 0
    output_tokens = 0

    for index, case in enumerate(cases, start=1):
        key = cache_key(model, prompt, case["input"])
        cache_file = CACHE_DIR / f"{key}.json"
        started = time.perf_counter()
        from_cache = cache_file.exists()
        try:
            if from_cache:
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
                raw_text = cached["raw_text"]
                response = cached.get("response", {})
                latency = float(cached.get("latency_s", 0.0))
            else:
                raw_text, response, latency = request_model(
                    base_url=provider["base_url"],
                    api_key=api_key,
                    model=model,
                    prompt=prompt,
                    text=case["input"],
                    max_retries=args.max_retries,
                    retry_delay=args.retry_delay,
                )
                cache_file.write_text(
                    json.dumps(
                        {
                            "raw_text": raw_text,
                            "response": response,
                            "latency_s": latency,
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
            parsed = parse_model_json(raw_text)
            valid = parsed is not None
            if valid:
                valid_count += 1
            expected = case["expected"]
            matching_fields = {}
            for field in fields:
                matches = valid and field in parsed and field in expected and values_equal(
                    parsed[field], expected[field]
                )
                matching_fields[field] = bool(matches)
                field_matches[field] += int(matches)
            complete = valid and all(matching_fields.values())
            complete_matches += int(complete)
            usage = response.get("usage", {}) if isinstance(response, dict) else {}
            input_tokens += int(usage.get("prompt_tokens", 0) or 0)
            output_tokens += int(usage.get("completion_tokens", 0) or 0)
            records.append(
                {
                    "id": case["id"],
                    "input": case["input"],
                    "expected": expected,
                    "raw": raw_text,
                    "parsed": parsed,
                    "validni_json": valid,
                    "shoda_poli": matching_fields,
                    "uplna_shoda": bool(complete),
                    "z_cache": from_cache,
                    "latence_s": latency,
                }
            )
            print(f"[{index}/{len(cases)}] id={case['id']} valid={valid} complete={complete}")
        except (OSError, KeyError, TypeError, ValueError, RuntimeError) as error:
            records.append(
                {
                    "id": case["id"],
                    "input": case["input"],
                    "expected": case["expected"],
                    "raw": None,
                    "parsed": None,
                    "validni_json": False,
                    "shoda_poli": {field: False for field in fields},
                    "uplna_shoda": False,
                    "chyba": str(error),
                    "z_cache": from_cache,
                    "latence_s": time.perf_counter() - started,
                }
            )
            print(f"[{index}/{len(cases)}] id={case['id']} chyba: {error}", file=sys.stderr)

    summary_entry = {
        "model": model,
        "poskytovatel": args.provider,
        "prompt": args.prompt,
        "sada": args.set,
        "pripadu": len(cases),
        "validni_json": valid_count / len(cases),
        "uplna_shoda": complete_matches / len(cases),
        "pole": {field: field_matches[field] / len(cases) for field in fields},
        "latence_s": sum(record["latence_s"] for record in records) / len(cases),
        "tokeny_vstup": input_tokens,
        "tokeny_vystup": output_tokens,
    }
    detailed_result = {
        "summary": summary_entry,
        "pripady": records,
    }
    result_file = result_path(args.provider, model, args.prompt, args.set)
    result_file.write_text(
        json.dumps(detailed_result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary_file = RESULTS_DIR / "summary.json"
    if summary_file.exists():
        summary = json.loads(summary_file.read_text(encoding="utf-8"))
    else:
        summary = {
            "student": "Kostiantyn Mamai",
            "uloha": "SMS zprÃ¡vy: phishing a typ podvodu",
            "behy": [],
        }
    summary.setdefault("behy", [])
    summary["behy"] = [
        run
        for run in summary["behy"]
        if not (
            run.get("model") == model
            and run.get("poskytovatel") == args.provider
            and run.get("prompt") == args.prompt
            and run.get("sada") == args.set
        )
    ]
    summary["behy"].append(summary_entry)
    summary_file.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary_entry, ensure_ascii=False, indent=2))
    print(f"VÃ½sledky: {result_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

