# With vs Without Cached Tokens (Problem 4)

I ran DD (gpt-6-luna) on all 12 practice documents in two setups. Every model call is saved in `output/cache_test.json`. To rerun it: `python cache_test.py`.

> **Rerun note:** the first version of this test was partly served by **Portkey's response cache**, which replays a stored answer when a request is identical to an earlier one (see surprise 5). DD now sends `x-portkey-cache-force-refresh: true` on every call, and all numbers below come from the fresh rerun. **All 48 calls got their own response ID**, so they are real model calls.

## The two setups

| Setup | How it is built |
|---|---|
| **With cache** | My instructions and the handbook are word-for-word identical at the start of every call, and every call carries the same `prompt_cache_key` (`cc-vendor-desk-dd`). OpenAI can then serve the handbook from its cache. |
| **Without cache** | Every model call starts with a fresh random line (`Request id: <random>`) placed *before* the handbook. Caching only works when the start of the prompt matches exactly, so no call can ever reuse a cached handbook. |

## Proof from the API's own token counts

| Check | Result |
|---|---|
| Without-cache calls that show cached tokens | **0 of 24** ✅ (the run counts) |
| With-cache calls that show cached tokens | **23 of 24** ✅ |
| Cached tokens per with-cache hit | 10,602 to 10,775 |
| Every call is a fresh model call (unique response ID, not a Portkey replay) | **48 of 48** ✅ |

The one with-cache miss was the first call on p11. It cost $0.0015 instead of about $0.0003. See surprise 3.

**Fairness note:** earlier runs with the same cache key had already stored the handbook, so the with-cache setup started warm, and p01 hit the cache on its first call. A cold start pays one extra write of about $0.0012. The p11 miss in this run already paid that once, so the total below includes about one cold start.

Each call in `cache_test.json` lists every count the API reported: input, cached input, cache write, uncached input, output, total, and reasoning tokens (under `details`). It also lists the dollar cost from `data/prices.json`.

## Results

Each document took **2 model calls**: one to read the document and one to give the answer. That makes 24 calls per setup.

| | With cache | Without cache |
|---|---|---|
| Model calls | 24 | 24 |
| Input tokens | 259,296 | 259,843 |
| …served from cache ($0.01/1M) | 245,669 | **0** |
| …written to cache ($0.125/1M) | 10,603 | 256,819 |
| …plain input ($0.10/1M) | 3,024 | 3,024 |
| Output tokens ($0.50/1M) | 1,426 | 1,385 |
| **Total cost (12 docs)** | **$0.004797** | **$0.033097** |
| **Cost per document** | **$0.000400** | **$0.002758** |
| Cost per model call | $0.000200 | $0.001379 |

**Savings: $0.028300 on 12 documents, or 85.5% less with cache.**

Math: 1 − 0.004797 ÷ 0.033097 = 0.855, so 85.5% saved.

## Real numbers vs my Problem 2 estimate

| | Problem 2 estimate (handbook only, 1 call) | Real (per model call) | Real (per document = 2 calls) |
|---|---|---|---|
| Tokens | 10,058 | ~10,730 (call 1) / ~10,880 (call 2) | ~21,600 |
| Cost without cache | $0.00100580 | $0.001379 | $0.002758 |
| Cost with cache | $0.00010058 | $0.000200 | $0.000400 |
| Savings | 90% | 85.5% | 85.5% |
| 1,000 documents, no cache | $1.01 | — | **$2.76** |
| 1,000 documents, with cache | $0.10 | — | **$0.40** |

- **The token count was close.** Each call sends about 10,730 tokens, about 7% more than the 10,058 estimate. The extra ~670 tokens are my instructions in `prompt.md`, the tool descriptions, the document path, and, on call 2, the document text.
- **The cost per document is about 2.7× the estimate** (no cache) and about 4× (with cache). The estimate assumed one call per document, but DD makes two, and each one resends the handbook. With cache, the part that can't be cached (the document, tool results, and output) is a bigger share of a much smaller bill.
- **Savings came in at 85.5%, not 90%.** Some tokens can never be cached: the document text, the answer, and one cache write. They pull the real savings below the 90% headline discount.

## Projection: 1,000 documents a day for 30 days (30,000 documents)

Using the real cost per document above:

| | Per day (1,000 docs) | 30 days (30,000 docs) |
|---|---|---|
| Without cache | $2.76 | **$82.74** |
| With cache | $0.40 | **$11.99** |
| **Saved by caching** | $2.36 | **$70.75 (85.5%)** |

Math: 30,000 × $0.0027581 = $82.74, and 30,000 × $0.0003998 = $11.99.

## What surprised me, and why

1. **"Without cache" costs more than plain input.** I expected the no-cache setup to pay the normal $0.10/1M input price. Instead, the API reported **256,819 cache-write tokens** at $0.125/1M, 25% more than normal. OpenAI tries to cache every long prompt. Because each prompt started with a new random line, each call paid to store a copy that was never reused. Without that write fee, the no-cache run would have cost $0.026677 instead of $0.033097. **A prompt that changes at the start is the worst case: you pay the write fee and never get the discount.**
2. **The handbook is paid for twice per document.** DD makes one call to request the document and a second to answer. The handbook goes out both times, so one document costs about 21,600 input tokens, not 10,058. Caching helps the most here, because the second call almost always hits the cache.
3. **Caching is not guaranteed.** In the with-cache setup, the first call on p11 missed the cache even though its prompt start was identical to the 10 documents before it, so it paid the full write price. OpenAI's cache is best-effort: a request can be routed to a server without the copy, and copies expire after a few minutes of no use. The run still hit the cache on 23 of 24 calls, so the shared `prompt_cache_key` mostly did its job.
4. **Small prompt edits reset the cache.** In Problem 3, one edit to `prompt.md` made the next run 5× more expensive ($0.0015 vs $0.0003). The cached copy no longer matched the prompt start, so the handbook had to be stored again.
5. **Portkey had a second, hidden cache that replayed whole answers.** Portkey (our gateway) has a *response cache* switched on for this API key. When a request is word-for-word identical to an earlier one, Portkey returns the stored answer (`x-portkey-cache-status: HIT`, same response ID) without calling the model. The first Problem 5 run finished 12 documents in 8 seconds with token counts identical to this test. That means it was a replay: the logged cost was copied from the earlier run, and the model never actually read the documents again. That is dangerous for testing, because you get the same answer every time and can't see the model's real behavior. DD now forces fresh calls, and the replayed entries in `output/usage_log.json` are flagged `"replayed_by_portkey": true`.
6. **Caching didn't change the answers, but answers vary from run to run.** Accuracy was 10/12 with cache and 9/12 without. p02 and p12 were wrong in both setups because of **hidden "revised price" text** (see Problem 5). The without-cache run also got p08 wrong this time, a clean document it usually gets right. That is ordinary model randomness, not caching: the model sees the same words either way.
