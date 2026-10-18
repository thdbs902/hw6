"""Count the tokens in the shop handbook and estimate what it costs per call (Problem 2)."""
import json
from pathlib import Path

import tiktoken

MODEL = "gpt-6-luna"
DATA = Path(__file__).parent / "data"

text = (DATA / "shop_handbook.md").read_text(encoding="utf-8")
tokens = len(tiktoken.get_encoding("o200k_base").encode(text))
p = json.loads((DATA / "prices.json").read_text())[MODEL]

uncached = tokens * p["input_per_1m"] / 1e6
cached = tokens * p["cached_input_per_1m"] / 1e6
write = tokens * p["cache_write_per_1m"] / 1e6

print(f"handbook tokens: {tokens:,}")
print(f"1 call   no cache: ${uncached:.8f} | cache write: ${write:.8f} | cache hit: ${cached:.8f}")
print(f"1000 calls no cache: ${uncached * 1000:.4f} | with cache (1 write + 999 hits): ${write + 999 * cached:.4f}")
