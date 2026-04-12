"""Tenzro Solana MCP Server — Jupiter swaps, SPL tokens, Metaplex NFTs, staking, SNS."""

from __future__ import annotations

import argparse
import json
import os

import httpx
from fastmcp import FastMCP

mcp = FastMCP("Tenzro Solana")

SOLANA_RPC = os.environ.get(
    "SOLANA_RPC_URL",
    "https://lb.drpc.org/ogrpc?network=solana&dkey=demo",
)
JUPITER_QUOTE_URL = "https://api.jup.ag/swap/v1/quote"
JUPITER_PRICE_URL = "https://api.jup.ag/price/v3"
SNS_PROXY_URL = "https://sns-sdk-proxy.bonfida.com"
DAS_URL = os.environ.get("DAS_URL", SOLANA_RPC)

TIMEOUT = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _sol_rpc(method: str, params: list | None = None) -> dict | list | None:
    """Send a JSON-RPC request to the Solana cluster."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            SOLANA_RPC,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []},
        )
        body = resp.json()
        if "error" in body:
            return {"error": body["error"]}
        return body.get("result")


async def _das_rpc(method: str, params: dict) -> dict | None:
    """Send a JSON-RPC request to a Metaplex DAS-compatible endpoint."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            DAS_URL,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        )
        body = resp.json()
        if "error" in body:
            return {"error": body["error"]}
        return body.get("result")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool
async def solana_swap(
    input_mint: str,
    output_mint: str,
    amount: int,
    slippage_bps: int = 50,
) -> str:
    """Get a Jupiter DEX aggregator swap quote.

    Args:
        input_mint: Input token mint address.
        output_mint: Output token mint address.
        amount: Amount in smallest unit (lamports / token base units).
        slippage_bps: Slippage tolerance in basis points (default 50 = 0.5%).
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            JUPITER_QUOTE_URL,
            params={
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount),
                "slippageBps": slippage_bps,
            },
        )
        data = resp.json()
    return json.dumps(data, indent=2)


@mcp.tool
async def solana_get_price(token_ids: str) -> str:
    """Get token prices via Jupiter Price API v3.

    Args:
        token_ids: Comma-separated mint addresses (e.g. "So11...1112,EPjF...pump").
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(JUPITER_PRICE_URL, params={"ids": token_ids})
        data = resp.json()
    return json.dumps(data, indent=2)


@mcp.tool
async def solana_stake(
    validator_vote_account: str,
    amount_sol: float,
    staker_pubkey: str,
) -> str:
    """Build staking instructions for a Solana validator.

    Returns the instruction parameters needed to create a stake account and
    delegate to the given validator. The caller must sign and submit the
    resulting transaction.

    Args:
        validator_vote_account: Vote account address of the validator.
        amount_sol: Amount of SOL to stake.
        staker_pubkey: Public key of the staker (funding account).
    """
    lamports = int(amount_sol * 1_000_000_000)
    instructions = {
        "type": "stake_delegation",
        "staker": staker_pubkey,
        "validator_vote_account": validator_vote_account,
        "lamports": lamports,
        "sol": amount_sol,
        "steps": [
            "CreateAccount (SystemProgram) with Stake111... owner",
            "Initialize (StakeProgram) with staker as authorized",
            "DelegateStake (StakeProgram) to validator vote account",
        ],
        "programs": {
            "system": "11111111111111111111111111111111",
            "stake": "Stake11111111111111111111111111111111111111",
        },
    }
    return json.dumps(instructions, indent=2)


@mcp.tool
async def solana_get_yield() -> str:
    """Get current staking APY data from Solana.

    Returns estimated APY based on epoch schedule and inflation parameters.
    """
    inflation = await _sol_rpc("getInflationRate")
    epoch_info = await _sol_rpc("getEpochInfo")

    if isinstance(inflation, dict) and "error" in inflation:
        return json.dumps({"error": inflation["error"]})
    if isinstance(epoch_info, dict) and "error" in epoch_info:
        return json.dumps({"error": epoch_info["error"]})

    total_rate = inflation.get("total", 0) if inflation else 0
    validator_rate = inflation.get("validator", 0) if inflation else 0

    result = {
        "inflation": {
            "total_rate": total_rate,
            "validator_rate": validator_rate,
            "epoch": inflation.get("epoch") if inflation else None,
        },
        "epoch_info": {
            "epoch": epoch_info.get("epoch") if epoch_info else None,
            "slot_index": epoch_info.get("slotIndex") if epoch_info else None,
            "slots_in_epoch": epoch_info.get("slotsInEpoch") if epoch_info else None,
        },
        "estimated_apy_pct": round(validator_rate * 100, 2) if validator_rate else None,
    }
    return json.dumps(result, indent=2)


@mcp.tool
async def solana_get_balance(address: str) -> str:
    """Get SOL balance for a Solana address.

    Args:
        address: Base-58 encoded Solana address.
    """
    result = await _sol_rpc("getBalance", [address])
    if isinstance(result, dict) and "error" in result:
        return json.dumps(result)
    value = result.get("value", 0) if isinstance(result, dict) else 0
    return json.dumps({"address": address, "lamports": value, "sol": value / 1e9})


@mcp.tool
async def solana_get_token_accounts(owner: str) -> str:
    """Get all SPL token accounts for an owner address.

    Args:
        owner: Base-58 encoded owner address.
    """
    result = await _sol_rpc(
        "getTokenAccountsByOwner",
        [
            owner,
            {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"},
            {"encoding": "jsonParsed"},
        ],
    )
    if isinstance(result, dict) and "error" in result:
        return json.dumps(result)

    accounts = []
    for item in (result or {}).get("value", []):
        info = item.get("account", {}).get("data", {}).get("parsed", {}).get("info", {})
        token_amount = info.get("tokenAmount", {})
        accounts.append({
            "pubkey": item.get("pubkey"),
            "mint": info.get("mint"),
            "owner": info.get("owner"),
            "amount": token_amount.get("uiAmountString"),
            "decimals": token_amount.get("decimals"),
        })
    return json.dumps({"owner": owner, "token_accounts": accounts, "count": len(accounts)}, indent=2)


@mcp.tool
async def solana_transfer(
    from_pubkey: str,
    to_pubkey: str,
    amount_sol: float,
    mint: str | None = None,
) -> str:
    """Build transfer instructions for SOL or an SPL token.

    Returns instruction parameters; the caller must sign and submit.

    Args:
        from_pubkey: Sender public key.
        to_pubkey: Recipient public key.
        amount_sol: Amount to send (in SOL for native, in token units for SPL).
        mint: SPL token mint address. Omit for native SOL transfer.
    """
    if mint:
        instructions = {
            "type": "spl_transfer",
            "from": from_pubkey,
            "to": to_pubkey,
            "mint": mint,
            "amount": amount_sol,
            "steps": [
                "Get or create associated token account for recipient",
                "Transfer (TokenProgram) from sender ATA to recipient ATA",
            ],
            "programs": {
                "token": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                "associated_token": "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
            },
        }
    else:
        lamports = int(amount_sol * 1_000_000_000)
        instructions = {
            "type": "sol_transfer",
            "from": from_pubkey,
            "to": to_pubkey,
            "lamports": lamports,
            "sol": amount_sol,
            "steps": ["Transfer (SystemProgram) lamports from sender to recipient"],
            "programs": {
                "system": "11111111111111111111111111111111",
            },
        }
    return json.dumps(instructions, indent=2)


@mcp.tool
async def solana_get_token_info(mint: str) -> str:
    """Get token metadata for an SPL token by mint address.

    Args:
        mint: Token mint address.
    """
    # Fetch on-chain mint info
    result = await _sol_rpc(
        "getAccountInfo",
        [mint, {"encoding": "jsonParsed"}],
    )
    if isinstance(result, dict) and "error" in result:
        return json.dumps(result)

    value = (result or {}).get("value")
    if not value:
        return json.dumps({"error": "Mint account not found", "mint": mint})

    parsed = value.get("data", {}).get("parsed", {}).get("info", {})
    supply = parsed.get("supply", "0")
    decimals = parsed.get("decimals", 0)

    # Try DAS for extended metadata (name, symbol, image)
    das_result = await _das_rpc("getAsset", {"id": mint})
    content = {}
    if isinstance(das_result, dict) and "error" not in das_result:
        content_block = das_result.get("content", {})
        metadata = content_block.get("metadata", {})
        content = {
            "name": metadata.get("name"),
            "symbol": metadata.get("symbol"),
            "image": content_block.get("links", {}).get("image"),
        }

    return json.dumps({
        "mint": mint,
        "decimals": decimals,
        "supply": supply,
        **content,
    }, indent=2)


@mcp.tool
async def solana_get_nft(asset_id: str) -> str:
    """Get NFT metadata via Metaplex Digital Asset Standard (DAS).

    Args:
        asset_id: The asset / mint address of the NFT.
    """
    result = await _das_rpc("getAsset", {"id": asset_id})
    if not result or (isinstance(result, dict) and "error" in result):
        return json.dumps(result or {"error": "No result"})

    content = result.get("content", {})
    metadata = content.get("metadata", {})
    ownership = result.get("ownership", {})

    return json.dumps({
        "id": result.get("id"),
        "name": metadata.get("name"),
        "symbol": metadata.get("symbol"),
        "description": metadata.get("description"),
        "image": content.get("links", {}).get("image"),
        "external_url": content.get("links", {}).get("external_url"),
        "owner": ownership.get("owner"),
        "delegate": ownership.get("delegate"),
        "collection": result.get("grouping", [{}])[0].get("group_value") if result.get("grouping") else None,
        "royalty_pct": result.get("royalty", {}).get("percent"),
        "attributes": metadata.get("attributes", []),
        "compressed": result.get("compression", {}).get("compressed", False),
    }, indent=2)


@mcp.tool
async def solana_get_nfts_by_owner(owner: str, page: int = 1, limit: int = 20) -> str:
    """Get NFTs owned by a Solana address via Metaplex DAS.

    Args:
        owner: Owner wallet address.
        page: Page number (1-indexed).
        limit: Results per page (max 1000).
    """
    result = await _das_rpc("getAssetsByOwner", {
        "ownerAddress": owner,
        "page": page,
        "limit": min(limit, 1000),
        "displayOptions": {"showCollectionMetadata": True},
    })
    if not result or (isinstance(result, dict) and "error" in result):
        return json.dumps(result or {"error": "No result"})

    items = []
    for asset in result.get("items", []):
        content = asset.get("content", {})
        metadata = content.get("metadata", {})
        items.append({
            "id": asset.get("id"),
            "name": metadata.get("name"),
            "symbol": metadata.get("symbol"),
            "image": content.get("links", {}).get("image"),
            "collection": asset.get("grouping", [{}])[0].get("group_value") if asset.get("grouping") else None,
            "compressed": asset.get("compression", {}).get("compressed", False),
        })

    return json.dumps({
        "owner": owner,
        "total": result.get("total", len(items)),
        "page": page,
        "limit": limit,
        "items": items,
    }, indent=2)


@mcp.tool
async def solana_get_slot() -> str:
    """Get the current slot height of the Solana cluster."""
    result = await _sol_rpc("getSlot")
    if isinstance(result, dict) and "error" in result:
        return json.dumps(result)
    return json.dumps({"slot": result})


@mcp.tool
async def solana_get_tps() -> str:
    """Get current transactions per second (TPS) from recent performance samples."""
    result = await _sol_rpc("getRecentPerformanceSamples", [5])
    if isinstance(result, dict) and "error" in result:
        return json.dumps(result)

    samples = result if isinstance(result, list) else []
    if not samples:
        return json.dumps({"tps": 0, "samples": 0})

    total_txs = sum(s.get("numTransactions", 0) for s in samples)
    total_secs = sum(s.get("samplePeriodSecs", 1) for s in samples)
    avg_tps = total_txs / total_secs if total_secs else 0

    return json.dumps({
        "avg_tps": round(avg_tps, 2),
        "samples": len(samples),
        "total_transactions": total_txs,
        "total_seconds": total_secs,
        "latest_slot": samples[0].get("slot") if samples else None,
    }, indent=2)


@mcp.tool
async def solana_get_transaction(signature: str) -> str:
    """Get transaction details by signature.

    Args:
        signature: Base-58 encoded transaction signature.
    """
    result = await _sol_rpc(
        "getTransaction",
        [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
    )
    if not result:
        return json.dumps({"error": "Transaction not found", "signature": signature})
    if isinstance(result, dict) and "error" in result:
        return json.dumps(result)

    meta = result.get("meta", {})
    tx = result.get("transaction", {})
    message = tx.get("message", {})

    return json.dumps({
        "signature": signature,
        "slot": result.get("slot"),
        "block_time": result.get("blockTime"),
        "fee": meta.get("fee"),
        "status": "success" if meta.get("err") is None else "failed",
        "error": meta.get("err"),
        "account_keys": [k.get("pubkey") if isinstance(k, dict) else k for k in message.get("accountKeys", [])],
        "instructions_count": len(message.get("instructions", [])),
        "log_messages": meta.get("logMessages", []),
        "pre_balances": meta.get("preBalances", []),
        "post_balances": meta.get("postBalances", []),
    }, indent=2)


@mcp.tool
async def solana_resolve_domain(domain: str) -> str:
    """Resolve a Bonfida SNS (.sol) domain to a Solana address.

    Args:
        domain: SNS domain name (e.g. "toly" or "toly.sol").
    """
    name = domain.removesuffix(".sol")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"{SNS_PROXY_URL}/resolve/{name}")
        if resp.status_code != 200:
            return json.dumps({"error": f"Resolution failed ({resp.status_code})", "domain": domain})
        data = resp.json()
    result = data.get("result") or data.get("s") or data
    return json.dumps({"domain": domain, "address": result}, indent=2)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Tenzro Solana MCP Server")
    parser.add_argument("--transport", choices=["http", "sse", "stdio"], default="http")
    parser.add_argument("--port", type=int, default=3003)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        mcp.run(transport="sse", host=args.host, port=args.port)
    else:
        mcp.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
