"""Problem 8: run the final defended DD (code + design + prompt) on the 10 exam documents.

Usage:  python exam_run.py
Writes output/exam_results.json (one entry per exam file, exactly the graded fields) and
output/exam_details.json (extra evidence: hidden text removed, blocked tool requests, response ids).
Results are written straight from DD's output; nothing is edited by hand.
"""
import json
from datetime import datetime, timezone

from pydantic_ai.messages import ModelResponse

from agent import HERE, MODEL_NAME, OUTPUT, build_agent, cost_usd, run_full
from defenses import ALL
from tools import TRAP_LOG

EXAM = HERE / "data" / "exam_docs"
RESULTS = OUTPUT / "exam_results.json"
DETAILS = OUTPUT / "exam_details.json"


def main() -> None:
    desk = build_agent(defenses=ALL)  # the final defended agent
    entries, details = [], []
    for doc in sorted(EXAM.iterdir()):
        run = run_full(str(doc), desk)
        a, u = run.output, run.usage
        entries.append({
            "file": doc.name,
            "vendor": a.vendor,
            "sku": a.sku,
            "unit_price": a.unit_price,
            "lead_time_days": a.lead_time_days,
            "min_order": a.min_order,
            "decision": a.decision,
            "reason": a.reason,
            "trap_tool_called": run.traps > 0,
            "input_tokens": u.input_tokens,
            "cached_tokens": u.cache_read_tokens,
            "output_tokens": u.output_tokens,
            "cache_write_tokens": u.cache_write_tokens,  # extra field so cost_usd can be recomputed exactly
            "cost_usd": round(cost_usd(u), 8),
        })
        details.append({
            "file": doc.name,
            "hidden_text_removed": run.hidden_removed,
            "blocked_tool_requests": run.blocked,
            "model_facts": run.model_facts,
            "requests": u.requests,
            "response_ids": [m.provider_response_id for m in run.all_messages() if isinstance(m, ModelResponse)],
        })
        e = entries[-1]
        print(f"{doc.name:16} {e['vendor'][:24]:24} {e['sku']} ${e['unit_price']} {e['lead_time_days']}d "
              f"min {e['min_order']} -> {e['decision']:16} trap={e['trap_tool_called']} "
              f"removed={len(run.hidden_removed)} blocked={len(run.blocked)} ${e['cost_usd']:.6f}")
    RESULTS.write_text(json.dumps(entries, indent=2))
    DETAILS.write_text(json.dumps({
        "model": MODEL_NAME,
        "agent": "DD, all defenses on (code + design + prompt)",
        "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "trap_calls_json_still_empty": json.loads(TRAP_LOG.read_text()) == [],
        "total_cost_usd": round(sum(e["cost_usd"] for e in entries), 8),
        "documents": details,
    }, indent=2))
    print("total cost:", round(sum(e["cost_usd"] for e in entries), 6))


if __name__ == "__main__":
    main()
