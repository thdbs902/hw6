# Handbook Size and Cost Estimate (Problem 2)

DD, the vendor desk agent, sends `data/shop_handbook.md` to **gpt-6-luna** on every call. This estimate covers the handbook only. It leaves out the vendor document, the instructions, and the model's answer.

## 1. Token count

| Measure | Value |
|---|---|
| Characters | 28,903 |
| Words | 6,127 |
| **Tokens (o200k_base)** | **10,058** |
| Tokens (cl100k_base, older tokenizer, for comparison) | 10,184 |

**Estimated handbook size: about 10,058 tokens.**

## 2. How I got it

1. I unzipped `data.zip` into `HW6/data/`.
2. I counted tokens with OpenAI's `tiktoken` library and its `o200k_base` tokenizer. That is the tokenizer current OpenAI models use. OpenAI does not publish a separate tokenizer for gpt-6-luna, so this is an estimate.
3. As a check, I also counted with the older `cl100k_base` tokenizer. It gave 10,184, about 1% higher, so the estimate is stable.
4. Run `pip install -r requirements.txt`, then `python count_tokens.py`, to repeat the count and the math below. No model call is made, so this costs $0.
5. Problem 4 will check this against the real `prompt_tokens` and `cached_tokens` from gpt-6-luna runs. The real count will be a little higher because each call adds its own instructions around the handbook.

## 3. Prices used (`data/prices.json`, gpt-6-luna, per 1M tokens)

| Type | Price |
|---|---|
| Input, not cached | $0.10 |
| Input, cache hit | $0.01 (90% off) |
| Cache write (first time the handbook is stored) | $0.125 |
| Output | $0.50 (not used here; the handbook is input only) |

## 4. The math

Formula: **cost = tokens × price per 1M ÷ 1,000,000**

**One call**
- Without caching: 10,058 × $0.10 ÷ 1,000,000 = **$0.00100580** (about 0.1¢)
- With caching, first call (cache write): 10,058 × $0.125 ÷ 1,000,000 = **$0.00125725**
- With caching, every later call (cache hit): 10,058 × $0.01 ÷ 1,000,000 = **$0.00010058** (about 0.01¢)

**1,000 calls**
- Without caching: 1,000 × $0.00100580 = **$1.0058**
- With caching: 1 cache write + 999 cache hits
  = $0.00125725 + 999 × $0.00010058
  = $0.00125725 + $0.10047942
  = **$0.1017**

## 5. Summary

| | 1 call | 1,000 calls |
|---|---|---|
| No caching | $0.00100580 | $1.0058 |
| With caching | $0.00010058 per hit ($0.00125725 for the first write) | $0.1017 |
| **Savings** | **90% per hit** | **$0.9041 (about 89.9%)** |

## 6. Assumptions

- The handbook sits at the very start of every prompt and never changes. Caching only reuses an identical starting chunk of the prompt.
- The cache stays warm between calls, so it is written once and reused 999 times. If calls are spread far apart, the cache can expire and has to be written again, which costs a little more.
- OpenAI caches prompts in blocks once they pass about 1,024 tokens. A few tokens at the very end may not be cached, which changes the cost very little.
