# HW6: DD, the Campus Customs vendor desk agent

DD reads **one** vendor document (HTML quote, PDF quote, or `.eml` email), pulls out the vendor, SKU, unit price, lead time, and minimum order, and recommends **recommend** or **do_not_recommend** following `data/shop_handbook.md`. It uses **gpt-6-luna only**, through Portkey.

- `send_email` and `approve_payment` are trap tools: they never send or pay anything, they only write to `output/trap_calls.json`.
- Campus Customs is a class setting. All vendors and documents are made up.

**Results page:** open `output/hw6_report.html` (one file, works offline).

## Run DD

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then put your PORTKEY_API_KEY in .env
python agent.py --doc data/practice_docs/p01_bluehen_quote.html
```

DD prints its answer, plus the tokens and dollar cost of the run. Every run is appended to `output/usage_log.json` and `output/audit_trail.json`.

| Option | What it does |
|---|---|
| *(default)* | All three defense layers on: code, design, prompt |
| `--no-defense` | The original Problem 3 agent, with no defenses |
| `--layers code,prompt` | Only the layers you list (`code`, `design`, `prompt`) |

## Reproduce the results

| Command | Problem | Output |
|---|---|---|
| `python count_tokens.py` | 2 · handbook size and cost (no API call) | `output/handbook_estimate.md` |
| `python cache_test.py` | 4 · with vs without prompt caching | `output/cache_test.json` / `.md` |
| `python attack_test.py` | 5 · attack the undefended agent | `output/attack_results.json` / `.md` |
| `python defense_test.py` | 6 · 12 docs × 5 defense setups | `output/defense_results.json` / `.md` |
| `python gate_test.py` | 6 · human sign-off gate proof (no API call) | prints PASS |
| `python make_attacks.py` | 7 · build my two red-team documents | `data/my_attacks/` |
| `python red_team_test.py` | 7 · my attacks, undefended vs defended | `output/red_team.json` / `.md` |
| `python exam_run.py` | 8 · final defended agent on the 10 exam docs | `output/exam_results.json` |
| `python build_report.py` | 9 · results page from the JSON files (no API call) | `output/hw6_report.html` |

## Files

- `agent.py`: entry point. `tools.py`: the tools. `models.py`: the structured types. `prompts/prompt.md`: my instructions (the handbook is added after them on every call).
- `defenses.py`: the safety layers. `output/harness.md` describes every field, tool, and defense in plain words.
- `AI_prompts.md`: every prompt I typed to my vibe coder, word for word.
- `.env` is never committed (see `.gitignore`). Use `.env.example` as the template.
