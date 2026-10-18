"""Problem 7: run my two red-team documents on DD with no defenses and with all defenses (3 tries each).

Usage:  python red_team_test.py
Saves output/red_team.json.
"""
import json
from datetime import datetime, timezone

import attack_test
import defense_test
from agent import HERE, MODEL_NAME, OUTPUT, build_agent, run_full
from defenses import ALL, NONE
from tools import TRAP_LOG

ATTACKS = HERE / "data" / "my_attacks"
DOCS = sorted(p for p in ATTACKS.glob("m*_*.*") if p.suffix != ".json")
KEY = {k["file"]: k for k in json.loads((ATTACKS / "my_attacks_key.json").read_text())}
TRIES = 3
RESULT = OUTPUT / "red_team.json"


def main() -> None:
    defense_test.KEY = attack_test.KEY = KEY  # score against my attack key instead of the practice key
    out = {}
    for d in (NONE, ALL):
        desk = build_agent(defenses=d)
        rows = []
        for doc in DOCS:
            for t in range(1, TRIES + 1):
                row = defense_test.score(doc, run_full(str(doc), desk))
                row["try"] = t
                rows.append(row)
                print(f"{d.label:20} {doc.name:26} try {t}: decision {row['decision']['got']:17} "
                      f"fooled={row['fooled']} sku={row['fields']['sku']['got']} min={row['fields']['min_order']['got']} "
                      f"removed={len(row['hidden_text_removed'])} ${row['cost_usd']:.6f}")
        out[d.label] = {"summary": {doc.name: {
            "tries": TRIES,
            "fooled": sum(r["fooled"] for r in rows if r["document"] == doc.name),
            "wrong_decisions": sum(not r["decision"]["match"] for r in rows if r["document"] == doc.name),
        } for doc in DOCS}, "results": rows}
    RESULT.write_text(json.dumps({
        "model": MODEL_NAME,
        "ran_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "trap_calls_json_still_empty": json.loads(TRAP_LOG.read_text()) == [],
        "setups": out,
    }, indent=2))
    print(json.dumps({k: v["summary"] for k, v in out.items()}, indent=2))


if __name__ == "__main__":
    main()
