"""Tenzro LI.FI MCP Server — 9 tools for LI.FI cross-chain DEX aggregation."""

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tenzro-lifi-mcp")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LIFI_API_URL = os.environ.get("LIFI_API_URL", "https://li.quest/v1")
LIFI_API_KEY = os.environ.get("LIFI_API_KEY", "")

_http = httpx.AsyncClient(timeout=30)


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if LIFI_API_KEY:
        headers["x-lifi-api-key"] = LIFI_API_KEY
    return headers


def _url(path: str) -> str:
    return f"{LIFI_API_URL}{path}"


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
async def lifi_get_chains() -> dict:
    """List all chains supported by LI.FI.

    Returns chain IDs, names, native tokens, and block explorer URLs.
    """
    resp = await _http.get(_url("/chains"), headers=_headers())
    resp.raise_for_status()
    data = resp.json()
    chains = data.get("chains", data if isinstance(data, list) else [])

    results = []
    for c in chains:
        results.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "key": c.get("key"),
            "chain_type": c.get("chainType"),
            "native_token": c.get("nativeToken", {}).get("symbol"),
            "block_explorer": c.get("metamask", {}).get("blockExplorerUrls", [None])[0],
        })

    return {"chains": results, "count": len(results)}


@mcp.tool()
async def lifi_get_tokens(chains: str | None = None) -> dict:
    """List tokens for one or more chains.

    Args:
        chains: Comma-separated chain IDs (e.g. "1,137,42161"). If omitted, returns tokens for all chains.
    """
    params: dict[str, Any] = {}
    if chains:
        params["chains"] = chains

    resp = await _http.get(_url("/tokens"), params=params, headers=_headers())
    resp.raise_for_status()
    data = resp.json()
    tokens = data.get("tokens", data)

    # Flatten per-chain token lists into summary
    summary: dict[str, int] = {}
    if isinstance(tokens, dict):
        for chain_id, token_list in tokens.items():
            summary[chain_id] = len(token_list) if isinstance(token_list, list) else 0

    return {"tokens": tokens, "chains_summary": summary}


@mcp.tool()
async def lifi_get_token(chain: str, token: str) -> dict:
    """Get token details by chain and address or symbol.

    Args:
        chain: Chain ID (e.g. "1" for Ethereum) or chain key (e.g. "eth")
        token: Token contract address or symbol (e.g. "USDC" or "0xA0b8...")
    """
    params = {"chain": chain, "token": token}
    resp = await _http.get(_url("/token"), params=params, headers=_headers())
    resp.raise_for_status()
    data = resp.json()

    return {
        "address": data.get("address"),
        "symbol": data.get("symbol"),
        "name": data.get("name"),
        "decimals": data.get("decimals"),
        "chain_id": data.get("chainId"),
        "logo_uri": data.get("logoURI"),
        "price_usd": data.get("priceUSD"),
    }


@mcp.tool()
async def lifi_get_tools() -> dict:
    """List available bridges and DEX aggregators used by LI.FI.

    Returns bridge and exchange tools with supported chains.
    """
    resp = await _http.get(_url("/tools"), headers=_headers())
    resp.raise_for_status()
    data = resp.json()

    bridges = data.get("bridges", [])
    exchanges = data.get("exchanges", [])

    bridge_summary = [
        {"name": b.get("name"), "key": b.get("key"), "chains": len(b.get("supportedChains", []))}
        for b in bridges
    ]
    exchange_summary = [
        {"name": e.get("name"), "key": e.get("key"), "chains": len(e.get("supportedChains", []))}
        for e in exchanges
    ]

    return {
        "bridges": bridge_summary,
        "exchanges": exchange_summary,
        "bridge_count": len(bridges),
        "exchange_count": len(exchanges),
    }


@mcp.tool()
async def lifi_get_connections(
    from_chain: str,
    to_chain: str,
    from_token: str | None = None,
    to_token: str | None = None,
) -> dict:
    """Get available connections (bridges/DEXes) between two chains.

    Args:
        from_chain: Source chain ID (e.g. "1")
        to_chain: Destination chain ID (e.g. "137")
        from_token: Optional source token address
        to_token: Optional destination token address
    """
    params: dict[str, Any] = {
        "fromChain": from_chain,
        "toChain": to_chain,
    }
    if from_token:
        params["fromToken"] = from_token
    if to_token:
        params["toToken"] = to_token

    resp = await _http.get(_url("/connections"), params=params, headers=_headers())
    resp.raise_for_status()
    data = resp.json()

    connections = data.get("connections", data if isinstance(data, list) else [])
    return {
        "connections": connections,
        "count": len(connections),
        "from_chain": from_chain,
        "to_chain": to_chain,
    }


@mcp.tool()
async def lifi_get_quote(
    from_chain: str,
    to_chain: str,
    from_token: str,
    to_token: str,
    from_amount: str,
    from_address: str,
    to_address: str | None = None,
    slippage: float = 0.03,
) -> dict:
    """Get a cross-chain swap quote with ready-to-sign calldata.

    Args:
        from_chain: Source chain ID (e.g. "1")
        to_chain: Destination chain ID (e.g. "137")
        from_token: Source token address or symbol
        to_token: Destination token address or symbol
        from_amount: Amount in smallest unit (e.g. wei)
        from_address: Sender wallet address
        to_address: Optional receiver address (defaults to from_address)
        slippage: Slippage tolerance (default 0.03 = 3%)
    """
    params: dict[str, Any] = {
        "fromChain": from_chain,
        "toChain": to_chain,
        "fromToken": from_token,
        "toToken": to_token,
        "fromAmount": from_amount,
        "fromAddress": from_address,
        "slippage": slippage,
    }
    if to_address:
        params["toAddress"] = to_address

    resp = await _http.get(_url("/quote"), params=params, headers=_headers())
    resp.raise_for_status()
    data = resp.json()

    # Extract key fields from the quote
    action = data.get("action", {})
    estimate = data.get("estimate", {})
    tx_request = data.get("transactionRequest", {})

    return {
        "id": data.get("id"),
        "type": data.get("type"),
        "tool": data.get("tool"),
        "from_token": action.get("fromToken", {}).get("symbol"),
        "to_token": action.get("toToken", {}).get("symbol"),
        "from_amount": action.get("fromAmount"),
        "to_amount": estimate.get("toAmount"),
        "to_amount_min": estimate.get("toAmountMin"),
        "approval_address": estimate.get("approvalAddress"),
        "execution_duration_seconds": estimate.get("executionDuration"),
        "fee_costs": estimate.get("feeCosts"),
        "gas_costs": estimate.get("gasCosts"),
        "transaction_request": {
            "to": tx_request.get("to"),
            "data": tx_request.get("data"),
            "value": tx_request.get("value"),
            "gas_limit": tx_request.get("gasLimit"),
            "gas_price": tx_request.get("gasPrice"),
            "chain_id": tx_request.get("chainId"),
        } if tx_request else None,
    }


@mcp.tool()
async def lifi_get_routes(
    from_chain_id: int,
    to_chain_id: int,
    from_token_address: str,
    to_token_address: str,
    from_amount: str,
    from_address: str,
    to_address: str | None = None,
    slippage: float = 0.03,
    max_price_impact: float = 0.4,
    allow_bridges: list[str] | None = None,
    deny_bridges: list[str] | None = None,
    allow_exchanges: list[str] | None = None,
    deny_exchanges: list[str] | None = None,
) -> dict:
    """Get advanced multi-step routes for a cross-chain swap.

    Supports split routes, multi-hop, and bridge/DEX filtering.

    Args:
        from_chain_id: Source chain ID (e.g. 1 for Ethereum)
        to_chain_id: Destination chain ID (e.g. 137 for Polygon)
        from_token_address: Source token address
        to_token_address: Destination token address
        from_amount: Amount in smallest unit
        from_address: Sender wallet address
        to_address: Optional receiver address
        slippage: Slippage tolerance (default 0.03 = 3%)
        max_price_impact: Maximum acceptable price impact (default 0.4 = 40%)
        allow_bridges: Optional whitelist of bridge keys
        deny_bridges: Optional blacklist of bridge keys
        allow_exchanges: Optional whitelist of exchange keys
        deny_exchanges: Optional blacklist of exchange keys
    """
    body: dict[str, Any] = {
        "fromChainId": from_chain_id,
        "toChainId": to_chain_id,
        "fromTokenAddress": from_token_address,
        "toTokenAddress": to_token_address,
        "fromAmount": from_amount,
        "fromAddress": from_address,
        "options": {
            "slippage": slippage,
            "maxPriceImpact": max_price_impact,
        },
    }
    if to_address:
        body["toAddress"] = to_address
    if allow_bridges:
        body["options"]["bridges"] = {"allow": allow_bridges}
    if deny_bridges:
        body["options"]["bridges"] = body["options"].get("bridges", {})
        body["options"]["bridges"]["deny"] = deny_bridges
    if allow_exchanges:
        body["options"]["exchanges"] = {"allow": allow_exchanges}
    if deny_exchanges:
        body["options"]["exchanges"] = body["options"].get("exchanges", {})
        body["options"]["exchanges"]["deny"] = deny_exchanges

    resp = await _http.post(
        _url("/advanced/routes"),
        json=body,
        headers=_headers(),
    )
    resp.raise_for_status()
    data = resp.json()

    routes = data.get("routes", [])
    route_summaries = []
    for r in routes:
        steps = r.get("steps", [])
        step_summaries = []
        for s in steps:
            step_summaries.append({
                "type": s.get("type"),
                "tool": s.get("tool"),
                "from_token": s.get("action", {}).get("fromToken", {}).get("symbol"),
                "to_token": s.get("action", {}).get("toToken", {}).get("symbol"),
                "from_chain": s.get("action", {}).get("fromChainId"),
                "to_chain": s.get("action", {}).get("toChainId"),
            })
        route_summaries.append({
            "id": r.get("id"),
            "from_amount": r.get("fromAmount"),
            "to_amount": r.get("toAmount"),
            "to_amount_min": r.get("toAmountMin"),
            "to_amount_usd": r.get("toAmountUSD"),
            "gas_cost_usd": r.get("gasCostUSD"),
            "steps": step_summaries,
            "tags": r.get("tags"),
        })

    return {
        "routes": route_summaries,
        "count": len(routes),
    }


@mcp.tool()
async def lifi_get_status(tx_hash: str, bridge: str | None = None, from_chain: str | None = None, to_chain: str | None = None) -> dict:
    """Track the status of a cross-chain transaction.

    Args:
        tx_hash: Source chain transaction hash
        bridge: Optional bridge tool name for faster lookup
        from_chain: Optional source chain ID
        to_chain: Optional destination chain ID
    """
    params: dict[str, Any] = {"txHash": tx_hash}
    if bridge:
        params["bridge"] = bridge
    if from_chain:
        params["fromChain"] = from_chain
    if to_chain:
        params["toChain"] = to_chain

    resp = await _http.get(_url("/status"), params=params, headers=_headers())
    resp.raise_for_status()
    data = resp.json()

    sending = data.get("sending", {})
    receiving = data.get("receiving", {})

    return {
        "status": data.get("status"),
        "substatus": data.get("substatus"),
        "sending": {
            "tx_hash": sending.get("txHash"),
            "chain_id": sending.get("chainId"),
            "amount": sending.get("amount"),
            "token": sending.get("token", {}).get("symbol") if sending.get("token") else None,
        } if sending else None,
        "receiving": {
            "tx_hash": receiving.get("txHash"),
            "chain_id": receiving.get("chainId"),
            "amount": receiving.get("amount"),
            "token": receiving.get("token", {}).get("symbol") if receiving.get("token") else None,
        } if receiving else None,
        "tool": data.get("tool"),
        "bridge_explorer_link": data.get("bridgeExplorerLink"),
    }


@mcp.tool()
async def lifi_get_gas_prices() -> dict:
    """Get current gas prices for all supported chains."""
    resp = await _http.get(_url("/gas/prices"), headers=_headers())
    resp.raise_for_status()
    data = resp.json()

    # Normalize response
    if isinstance(data, dict):
        chains = []
        for chain_id, prices in data.items():
            entry = {"chain_id": chain_id}
            if isinstance(prices, dict):
                entry.update({
                    "standard": prices.get("standard"),
                    "fast": prices.get("fast"),
                    "instant": prices.get("instant"),
                })
            else:
                entry["gas_price"] = prices
            chains.append(entry)
        return {"gas_prices": chains, "count": len(chains)}

    return {"gas_prices": data}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    mcp.run(transport="streamable-http", host="0.0.0.0", port=3008)


if __name__ == "__main__":
    main()
