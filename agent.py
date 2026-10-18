"""DD, the Campus Customs vendor desk agent.

Usage:  python agent.py --doc data/practice_docs/p01_bluehen_quote.html                 (all defenses on)
        python agent.py --doc data/practice_docs/p01_bluehen_quote.html --no-defense    (the Problem 3 agent)
        python agent.py --doc ... --layers code,prompt                                  (pick layers)
Reads one vendor document, extracts the key facts, recommends buy / don't buy per the handbook,
and appends the run to output/usage_log.json and output/audit_trail.json.
"""
import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")  # keep the terminal output clean

from dataclasses import dataclass, field  # noqa: E402

from dotenv import load_dotenv  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402
from pydantic_ai import Agent, DeferredToolRequests, DeferredToolResults, ToolDenied  # noqa: E402
from pydantic_ai.messages import ToolCallPart, ToolReturnPart  # noqa: E402
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402
from pydantic_ai.usage import UsageLimits  # noqa: E402

from defenses import ALL, NONE, Defenses, decide, ground  # noqa: E402
from models import DeskDeps, VendorDecision, VendorFacts  # noqa: E402
from tools import GATED_TOOLS, TOOLS, TRAP_LOG, append_json  # noqa: E402

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "output"
USAGE_LOG = OUTPUT / "usage_log.json"
AUDIT_LOG = OUTPUT / "audit_trail.json"
BLOCKED_LOG = OUTPUT / "blocked_actions.json"  # dangerous tool requests waiting for (and denied without) a human sign-off
SAFETY_START, SAFETY_END = "## Safety rules", "## End of safety rules"  # prompt layer lives between these

MODEL_NAME = "gpt-6-luna"  # the only model allowed in HW6 — deliberately not configurable
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
PRICES = json.loads((HERE / "data" / "prices.json").read_text())[MODEL_NAME]
SETTINGS = OpenAIResponsesModelSettings(openai_reasoning_effort="low", max_tokens=1_500)
# with cache (default): same prefix every call + one cache key, so OpenAI reuses the handbook
CACHE_SETTINGS = OpenAIResponsesModelSettings(**SETTINGS, openai_prompt_cache_key="cc-vendor-desk-dd")
NO_CACHE_SETTINGS = SETTINGS  # without cache: a unique nonce starts every call instead (see build_agent)
LIMITS = UsageLimits(request_limit=6, tool_calls_limit=6)

load_dotenv(HERE / ".env")
load_dotenv(HERE.parent / ".env")  # also accept a .env one folder up (my course folder keeps it there)


def build_model() -> OpenAIResponsesModel:
    """gpt-6-luna through Portkey's OpenAI-compatible gateway."""
    key = os.getenv("PORTKEY_API_KEY")
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set. Copy .env.example to .env and put your key in it.")
    client = AsyncOpenAI(
        api_key=key,
        base_url=PORTKEY_BASE_URL,
        default_headers={
            "x-portkey-api-key": key,
            "x-portkey-provider": "openai",
            # Portkey's response cache replays stored answers for identical requests; always ask the model fresh
            "x-portkey-cache-force-refresh": "true",
        },
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


def build_instructions(prompt_rules: bool = True) -> str:
    """My instructions for DD followed by the full handbook (sent on every call, never changes).
    prompt_rules=False cuts out the safety-rules section of prompt.md, giving the Problem 3 prompt."""
    prompt = (HERE / "prompts" / "prompt.md").read_text(encoding="utf-8")
    if not prompt_rules:
        prompt = re.sub(rf"{SAFETY_START}.*?{SAFETY_END}\n*", "", prompt, flags=re.S)
    handbook = (HERE / "data" / "shop_handbook.md").read_text(encoding="utf-8")
    return f"{prompt}\n\n{handbook}"


@dataclass
class Desk:
    """DD = a PydanticAI agent plus the safety layers it was built with."""

    agent: Agent
    defenses: Defenses


def build_agent(cache: bool = True, defenses: Defenses = ALL) -> Desk:
    """cache=True: the handbook prefix is identical on every call, so it is reused from cache.
    cache=False: a fresh random nonce starts every model call, so no prefix ever matches a cached one.
    defenses: which safety layers are on (ALL by default, NONE = the Problem 3 agent)."""
    text = build_instructions(prompt_rules=defenses.prompt)
    if cache:
        instructions = text
    else:
        def instructions() -> str:  # re-evaluated on every model request
            return f"Request id: {uuid4().hex}\n\n{text}"
    agent = Agent(
        build_model(),
        instructions=instructions,
        deps_type=DeskDeps,
        # design layer: the model only extracts facts and dangerous tools need a human sign-off
        output_type=[VendorFacts, DeferredToolRequests] if defenses.design else VendorDecision,
        tools=GATED_TOOLS if defenses.design else TOOLS,
        model_settings=CACHE_SETTINGS if cache else NO_CACHE_SETTINGS,
    )
    return Desk(agent, defenses)


def cost_usd(usage) -> float:
    """Dollar cost from the token counts the API reported, using data/prices.json."""
    cached = usage.cache_read_tokens
    written = usage.cache_write_tokens
    uncached = usage.input_tokens - cached - written
    return (
        uncached * PRICES["input_per_1m"]
        + cached * PRICES["cached_input_per_1m"]
        + written * PRICES["cache_write_per_1m"]
        + usage.output_tokens * PRICES["output_per_1m"]
    ) / 1_000_000


def tool_calls(messages) -> list[dict]:
    """Every tool call in the run with its arguments and a short result."""
    results = {
        p.tool_call_id: str(p.content)
        for m in messages for p in m.parts if isinstance(p, ToolReturnPart)
    }
    calls = []
    for m in messages:
        for p in m.parts:
            if isinstance(p, ToolCallPart) and p.tool_name != "final_result":  # final answer is logged separately
                result = results.get(p.tool_call_id, "")
                calls.append({
                    "tool": p.tool_name,
                    "args": p.args_as_dict(),
                    "result": result if len(result) <= 200 else result[:200] + "...",
                })
    return calls


@dataclass
class DeskRun:
    """One finished DD run: the answer plus everything the logs and tests need."""

    output: VendorDecision
    messages: list
    usage: object
    defenses: Defenses
    model_facts: dict | None = None  # design layer: what the model extracted before grounding
    blocked: list[dict] = field(default_factory=list)  # dangerous tool requests stopped at the sign-off gate
    hidden_removed: list[str] = field(default_factory=list)  # code layer: hidden text taken out
    traps: int = 0

    def all_messages(self) -> list:
        return self.messages


def run(doc: str, desk: Desk | None = None) -> VendorDecision:
    return run_full(doc, desk).output


def run_full(doc: str, desk: Desk | None = None) -> DeskRun:
    """Run DD on one document, write the logs, and return the full run."""
    doc_path = Path(doc).resolve()
    if not doc_path.exists():
        raise SystemExit(f"Document not found: {doc}")
    if not TRAP_LOG.exists():
        TRAP_LOG.write_text("[]")  # start the trap log as an empty list
    traps_before = len(json.loads(TRAP_LOG.read_text()))

    desk = desk or build_agent()
    d = desk.defenses
    deps = DeskDeps(doc_path=doc_path, defenses=d)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rel = doc_path.relative_to(HERE) if doc_path.is_relative_to(HERE) else doc_path
    result = desk.agent.run_sync(f"Vendor document path: {rel}", deps=deps, usage_limits=LIMITS)

    # design layer: a request for send_email / approve_payment pauses the run for a human sign-off.
    # No human is in this loop, so the request is denied, logged for review, and DD carries on.
    blocked = []
    while isinstance(result.output, DeferredToolRequests):
        approvals = {}
        for call in result.output.approvals:
            entry = {"time": started, "document": str(rel), "tool": call.tool_name, "args": call.args_as_dict(),
                     "status": "denied: needs a human sign-off"}
            blocked.append(entry)
            append_json(BLOCKED_LOG, entry)
            approvals[call.tool_call_id] = ToolDenied("Blocked: this action needs a human sign-off. Finish the vendor review only.")
        result = desk.agent.run_sync(
            message_history=result.all_messages(),
            deferred_tool_results=DeferredToolResults(approvals=approvals),
            deps=deps, usage_limits=LIMITS, usage=result.usage,
        )

    model_facts = None
    if d.design:  # design layer: code grounds the numbers and makes the decision
        facts = result.output
        model_facts = facts.model_dump()
        price = ground(facts.unit_price, deps.text_seen)
        lead = ground(facts.lead_time_days, deps.text_seen)
        min_order = ground(facts.min_order, deps.text_seen)
        decision, reason = decide(facts.vendor, facts.sku, price, lead, min_order)
        answer = VendorDecision(vendor=facts.vendor, sku=facts.sku, unit_price=price, lead_time_days=lead,
                                min_order=min_order, decision=decision, reason=reason)
    else:
        answer = result.output

    u = result.usage
    traps = len(json.loads(TRAP_LOG.read_text())) - traps_before
    append_json(USAGE_LOG, {
        "document": str(rel),
        "time": started,
        "model": MODEL_NAME,
        "defenses": d.label,
        "requests": u.requests,
        "input_tokens": u.input_tokens,
        "cached_input_tokens": u.cache_read_tokens,
        "cache_write_tokens": u.cache_write_tokens,
        "output_tokens": u.output_tokens,
        "reasoning_tokens": u.details.get("reasoning_tokens", 0),
        "total_tokens": u.input_tokens + u.output_tokens,
        "cost_usd": round(cost_usd(u), 8),
    })
    append_json(AUDIT_LOG, {
        "document": str(rel),
        "time": started,
        "defenses": d.label,
        "tool_calls": tool_calls(result.all_messages()),
        "hidden_text_removed": deps.hidden_removed,
        "blocked_tool_requests": blocked,
        "trap_calls_this_run": traps,
        "model_facts": model_facts,
        "final_answer": answer.model_dump(),
    })
    if traps:
        print(f"WARNING: {traps} trap call(s) this run — this document took over DD. See output/trap_calls.json")
    if blocked:
        print(f"BLOCKED: {len(blocked)} dangerous tool request(s) stopped at the human sign-off gate. See {BLOCKED_LOG.name}")
    return DeskRun(answer, result.all_messages(), u, d, model_facts, blocked, deps.hidden_removed, traps)


def parse_layers(text: str) -> Defenses:
    names = {n.strip() for n in text.split(",") if n.strip()}
    unknown = names - {"code", "design", "prompt"}
    if unknown:
        raise SystemExit(f"Unknown layer(s): {', '.join(sorted(unknown))}. Use code, design, prompt.")
    return Defenses(code="code" in names, design="design" in names, prompt="prompt" in names)


def main() -> None:
    parser = argparse.ArgumentParser(description="DD, the Campus Customs vendor desk agent")
    parser.add_argument("--doc", required=True, help="path to one vendor document (html, pdf, or eml)")
    parser.add_argument("--no-defense", action="store_true", help="run the Problem 3 agent with no safety layers")
    parser.add_argument("--layers", help="comma list of layers to turn on: code,design,prompt (default: all)")
    args = parser.parse_args()
    defenses = NONE if args.no_defense else parse_layers(args.layers) if args.layers else ALL
    answer = run(args.doc, build_agent(defenses=defenses))
    print(json.dumps(answer.model_dump(), indent=2))
    last = json.loads(USAGE_LOG.read_text())[-1]
    print(f"defenses: {defenses.label} | tokens: {last['input_tokens']:,} in ({last['cached_input_tokens']:,} cached), "
          f"{last['output_tokens']:,} out | cost ${last['cost_usd']:.6f}")


if __name__ == "__main__":
    main()
