#!/usr/bin/env python3
"""Scrape DexScreener for top AI/agent tokens on Solana — Issue #142 (v2 with User-Agent)"""
import json, urllib.request, sys, time

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://dexscreener.com",
    "Referer": "https://dexscreener.com/",
}

SEED_TOKENS = [
    "WATT", "Render", "Nosana", "Griffain", "NEURON",
    "Hive AI", "Zerebro", "Vvaifu", "Rise", "KIP",
    "Mars", "TARS", "Cog", "Swarms", "AI16Z", "ELIZA",
    "FARTCOIN", "ACT", "GOAT", "SHELL", "CAI",
    "H4CK", "MORPH", "MYRO", "BONSOL", "GRIFFAIN",
]

SEARCH_TERMS = [
    "AI agent", "artificial intelligence", "autonomous agent",
    "compute", "decentralized AI", "machine learning",
    "AI token", "agent token", "Solana AI",
]

def dexscreener_search(query):
    url = f"https://api.dexscreener.com/latest/dex/search/?q={urllib.parse.quote(query)}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  Error on '{query}': {e}", file=sys.stderr)
        return {"pairs": []}

def dexscreener_token_profiles():
    """Fetch token profiles from DexScreener"""
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  Error fetching profiles: {e}", file=sys.stderr)
        return []

def dexscreener_token_pairs(chain, token_addr):
    url = f"https://api.dexscreener.com/token-pairs/v1/{chain}/{token_addr}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return []

if __name__ == "__main__":
    import urllib.parse

    # Try token profiles first
    print("Fetching token profiles...", file=sys.stderr)
    profiles = dexscreener_token_profiles()

    # Collect pairs from search
    print("Searching DexScreener...", file=sys.stderr)
    pairs = []

    for token in SEED_TOKENS:
        time.sleep(0.15)  # rate limit
        data = dexscreener_search(token)
        for p in data.get("pairs", []):
            if p.get("chainId") == "solana":
                pairs.append(p)
        print(f"  {token}: {len(data.get('pairs', []))} results", file=sys.stderr)

    for term in SEARCH_TERMS:
        time.sleep(0.2)
        data = dexscreener_search(term)
        for p in data.get("pairs", []):
            if p.get("chainId") == "solana":
                pairs.append(p)
        print(f"  '{term}': {len(data.get('pairs', []))} results", file=sys.stderr)

    print(f"Total raw pairs: {len(pairs)}", file=sys.stderr)

    # Deduplicate by base token address
    by_token = {}
    for p in pairs:
        addr = p.get("baseToken", {}).get("address", "")
        if not addr:
            continue
        if addr not in by_token:
            by_token[addr] = p
        else:
            # Keep higher liquidity
            old_liq = float(by_token[addr].get("liquidity", {}).get("usd", 0) or 0)
            new_liq = float(p.get("liquidity", {}).get("usd", 0) or 0)
            if new_liq > old_liq:
                by_token[addr] = p

    # Extract info
    def extract(p):
        base = p.get("baseToken", {})
        liq = p.get("liquidity", {}) or {}
        vol = p.get("volume", {}) or {}
        return {
            "name": base.get("name", "?"),
            "symbol": base.get("symbol", "?"),
            "contract_address": base.get("address", "?"),
            "chain": p.get("chainId", "?"),
            "market_cap_usd": str(p.get("fdv", "?") or "?"),
            "price_usd": p.get("priceUsd", "?"),
            "volume_24h_usd": str(vol.get("h24", "?") or "?"),
            "liquidity_usd": str(liq.get("usd", "?") or "?"),
            "pair_address": p.get("pairAddress", "?"),
            "dex_url": p.get("url", "?"),
            "txns_24h_buys": p.get("txns", {}).get("h24", {}).get("buys", "?"),
            "txns_24h_sells": p.get("txns", {}).get("h24", {}).get("sells", "?"),
        }

    tokens = [extract(p) for p in by_token.values()]

    # Sort by market cap descending
    def sort_key(t):
        try:
            return -float(t["market_cap_usd"]) if t["market_cap_usd"] != "?" and t["market_cap_usd"] else 0
        except:
            return 0
    tokens.sort(key=sort_key)

    # Top 50
    tokens = tokens[:50]

    output = {
        "source": "DexScreener API",
        "query_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "count": len(tokens),
        "tokens": tokens,
    }

    # Write JSON
    json_path = "/home/desh/projects/wattcoin/research/dexscreener-top50-ai-tokens.json"
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"JSON: {json_path} ({len(tokens)} tokens)", file=sys.stderr)

    # Build markdown
    md = f"""# Top AI/Agent Tokens on Solana — DexScreener Data

**Source**: DexScreener API  
**Date**: {time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())}  
**Total tokens found**: {len(tokens)}  

## Token Rankings (by Market Cap)

| # | Token | Symbol | Price (USD) | Market Cap | 24h Volume | Liquidity |
|---|-------|--------|------------|------------|-----------|-----------|
"""

    for i, t in enumerate(tokens, 1):
        try:
            mc = f"${float(t['market_cap_usd']):,.0f}" if t["market_cap_usd"] and t["market_cap_usd"] != "?" else "?"
        except: mc = "?"
        try:
            vol = f"${float(t['volume_24h_usd']):,.0f}" if t["volume_24h_usd"] and t["volume_24h_usd"] != "?" else "?"
        except: vol = "?"
        try:
            liq = f"${float(t['liquidity_usd']):,.0f}" if t["liquidity_usd"] and t["liquidity_usd"] != "?" else "?"
        except: liq = "?"
        price = f"${float(t['price_usd']):,.8f}" if t["price_usd"] and t["price_usd"] != "?" else "?"
        md += f"| {i} | {t['name']} | ${t['symbol']} | {price} | {mc} | {vol} | {liq} |\n"

    with_mc = sum(1 for t in tokens if t["market_cap_usd"] and t["market_cap_usd"] != "?")
    with_liq = sum(1 for t in tokens if t["liquidity_usd"] and t["liquidity_usd"] != "?" and float(t["liquidity_usd"] or 0) > 10000)

    md += f"""
## Summary

- **Unique tokens found**: {len(tokens)}
- **Tokens with market cap data**: {with_mc}
- **Tokens with liquidity > $10K**: {with_liq}

## Data

See [`dexscreener-top50-ai-tokens.json`](dexscreener-top50-ai-tokens.json) for complete dataset including contract addresses, pair addresses, and 24h transaction counts.

---
*Data collected via DexScreener API for WattCoin bounty #142.*
"""

    md_path = "/home/desh/projects/wattcoin/research/dexscreener-top50-ai-tokens.md"
    with open(md_path, "w") as f:
        f.write(md)
    print(f"Markdown: {md_path}", file=sys.stderr)
    print("Done!", file=sys.stderr)
