"""Problem 4: run DD on all 12 practice documents with and without prompt caching.

Usage:  python cache_test.py
Saves every model call to output/cache_test.json and checks the API's token counts prove each setup.
"""
import json
from datetime import datetime, timezone

from pydantic_ai.messages import ModelResponse

from agent import HERE, MODEL_NAME, OUTPUT, PRICES, build_agent, run_full
from defenses import NONE

DOCS = sorted((HERE / "data" / "practice_docs").iterdir())
KEY = {k["file"]: k for k in json.loads((HERE / "data" / "practice_key.json").read_text())}
RESULT = OUTPUT / "cache_test.json"


def call_cost(u) -> float:
    uncached = u.input_tokens - u.cache_read_tokens - u.cache_write_tokens
    return (
        uncached * PRICES["input_per_1m"]
        + u.cache_read_tokens * PRICES["cached_input_per_1m"]
        + u.cache_write_tokens * PRICES["cache_write_per_1m"]
        + u.output_tokens * PRICES["output_per_1m"]
    ) / 1_000_000


def run_setup(setup: str) -> tuple[list[dict], list[dict]]:
    agent = build_agent(cache=setup == "with_cache", defenses=NONE)  # the Problem 3 agent
    calls, runs = [], []
    for doc in DOCS:
        result = run_full(str(doc), agent)
        responses = [m for m in result.all_messages() if isinstance(m, ModelResponse)]
        for i, m in enumerate(responses, 1):
            u = m.usage
            calls.append({
                "setup": setup,
                "document": doc.name,
                "call": i,
                "time": m.timestamp.isoformat(timespec="seconds"),
                "response_id": m.provider_response_id,
                "input_tokens": u.input_tokens,
                "cached_input_tokens": u.cache_read_tokens,
                "cache_write_tokens": u.cache_write_tokens,
                "uncached_input_tokens": u.input_tokens - u.cache_read_tokens - u.cache_write_tokens,
                "output_tokens": u.output_tokens,
                "total_tokens": u.input_tokens + u.output_tokens,
                "details": dict(u.details),  # every other count the API reported, e.g. reasoning_tokens
                "cost_usd": round(call_cost(u), 8),
            })
        out = result.output
        runs.append({
            "setup": setup,
            "document": doc.name,
            "calls": len(responses),
            "cost_usd": round(sum(c["cost_usd"] for c in calls if c["document"] == doc.name), 8),
            "decision": out.decision,
            "matches_key": out.decision == KEY[doc.name]["decision"],
        })
        print(f"{setup:13} {doc.name:32} {runs[-1]['cost_usd']:.6f}  {out.decision}")
    return calls, runs


def check(calls: list[dict]) -> dict:
    """Prove each setup with the API's own counts."""
    no = [c for c in calls if c["setup"] == "without_cache"]
    yes = [c for c in calls if c["setup"] == "with_cache"]
    return {
        "without_cache_calls_with_cached_tokens": sum(c["cached_input_tokens"] > 0 for c in no),
        "with_cache_calls_with_cached_tokens": sum(c["cached_input_tokens"] > 0 for c in yes),
        "with_cache_calls_total": len(yes),
        "without_cache_valid": all(c["cached_input_tokens"] == 0 for c in no),
        # every call got its own response id = a real model call, not a replay from Portkey's response cache
        "all_calls_fresh": len({c["response_id"] for c in calls}) == len(calls),
    }


def main() -> None:
    calls, runs = [], []
    for setup in ("with_cache", "without_cache"):
        c, r = run_setup(setup)
        calls += c
        runs += r
    proof = check(calls)
    RESULT.write_text(json.dumps({
        "model": MODEL_NAME,
        "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "prices_per_1m": PRICES,
        "proof": proof,
        "runs": runs,
        "calls": calls,
    }, indent=2))
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
