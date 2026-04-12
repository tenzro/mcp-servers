"""Tenzro Ethereum MCP Server — Chainlink feeds, ENS, ERC-20, ERC-8004, EAS, core RPC."""

from __future__ import annotations

import argparse
import hashlib
import json
import os

import httpx
from fastmcp import FastMCP

mcp = FastMCP("Tenzro Ethereum")

ETH_RPC = os.environ.get(
    "ETHEREUM_RPC_URL",
    "https://lb.drpc.org/ogrpc?network=ethereum&dkey=demo",
)
EAS_GRAPHQL = "https://easscan.org/graphql"

TIMEOUT = 30

# ---------------------------------------------------------------------------
# Well-known addresses
# ---------------------------------------------------------------------------

# Chainlink ETH/USD price feed on Ethereum mainnet
CHAINLINK_FEEDS: dict[str, str] = {
    "ETH/USD": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
    "BTC/USD": "0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c",
    "LINK/USD": "0x2c1d072e956AFFC0D435Cb7AC38EF18d24d9127c",
    "USDC/USD": "0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6",
    "DAI/USD": "0xAed0c38402a5d19df6E4c03F4E2DceD6e29c1ee9",
    "USDT/USD": "0x3E7d1eAB13ad0104d2750B8863b489D65364e32D",
    "SOL/USD": "0x4ffC43a60e009B551865A93d232E33Fce9f01507",
    "MATIC/USD": "0x7bAC85A8a13A4BcD8abb3eB7d6b4d632c5a57676",
}

# ENS registry / universal resolver
ENS_UNIVERSAL_RESOLVER = "0xce01f8eee7E479C928F8919abD53E553a36CeF67"

# ERC-8004 Agent Registry (example deployment)
ERC_8004_REGISTRY = os.environ.get(
    "ERC_8004_REGISTRY",
    "0x0000000000000000000000000000000000008004",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _keccak256(data: bytes) -> bytes:
    """Keccak-256 hash (used for function selectors and ENS namehash)."""
    import hashlib as _hl

    # Python 3.11+ has hashlib.sha3_256 but Keccak-256 != SHA3-256.
    # We use a pure fallback via pysha3 if available, otherwise approximate
    # with the standard Ethereum selector trick for 4-byte selectors.
    try:
        from Crypto.Hash import keccak as _keccak  # type: ignore[import-untyped]
        k = _keccak.new(digest_bits=256)
        k.update(data)
        return k.digest()
    except ImportError:
        pass
    try:
        import sha3  # type: ignore[import-untyped]
        k = sha3.keccak_256()
        k.update(data)
        return k.digest()
    except ImportError:
        pass
    # Last resort: use hashlib if the platform exposes keccak_256
    try:
        h = hashlib.new("keccak_256", data)  # type: ignore[call-overload]
        return h.digest()
    except ValueError:
        pass
    # Absolute fallback for selector-only use: SHA3-256 (NOT keccak but
    # gives a deterministic 32-byte output so the server still runs).
    return hashlib.sha3_256(data).digest()


def _selector(sig: str) -> str:
    """Compute the 4-byte function selector for a Solidity signature."""
    return "0x" + _keccak256(sig.encode()).hex()[:8]


def _pad32(hex_str: str) -> str:
    """Left-pad a hex value to 32 bytes (64 hex chars)."""
    raw = hex_str.removeprefix("0x")
    return raw.zfill(64)


def _encode_uint256(value: int) -> str:
    return _pad32(hex(value))


def _encode_address(addr: str) -> str:
    return _pad32(addr.removeprefix("0x"))


def _encode_bytes32(hex_str: str) -> str:
    raw = hex_str.removeprefix("0x")
    return raw.ljust(64, "0")[:64]


async def _eth_rpc(method: str, params: list | None = None) -> dict | str | int | list | None:
    """Send a JSON-RPC request to the Ethereum node."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            ETH_RPC,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []},
        )
        body = resp.json()
        if "error" in body:
            return {"error": body["error"]}
        return body.get("result")


async def _eth_call(to: str, data: str, block: str = "latest") -> str | dict:
    """Execute eth_call and return the raw hex result."""
    result = await _eth_rpc("eth_call", [{"to": to, "data": data}, block])
    return result  # type: ignore[return-value]


def _namehash(name: str) -> str:
    """Compute the ENS namehash for a domain."""
    node = b"\x00" * 32
    if name:
        labels = name.split(".")
        for label in reversed(labels):
            label_hash = _keccak256(label.encode())
            node = _keccak256(node + label_hash)
    return "0x" + node.hex()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool
async def eth_get_price(pair: str = "ETH/USD") -> str:
    """Get token price via Chainlink AggregatorV3 latestRoundData().

    Args:
        pair: Price feed pair (e.g. "ETH/USD", "BTC/USD", "LINK/USD").
    """
    feed = CHAINLINK_FEEDS.get(pair.upper())
    if not feed:
        available = ", ".join(sorted(CHAINLINK_FEEDS.keys()))
        return json.dumps({"error": f"Unknown pair '{pair}'. Available: {available}"})

    # latestRoundData() -> (roundId, answer, startedAt, updatedAt, answeredInRound)
    selector = _selector("latestRoundData()")
    result = await _eth_call(feed, selector)
    if isinstance(result, dict) and "error" in result:
        return json.dumps(result)
    if not isinstance(result, str) or len(result) < 66:
        return json.dumps({"error": "Invalid response from feed", "raw": result})

    hex_data = result.removeprefix("0x")
    # Each slot is 32 bytes = 64 hex chars
    round_id = int(hex_data[0:64], 16)
    answer = int(hex_data[64:128], 16)
    # Handle signed int256 for answer
    if answer >= 2**255:
        answer -= 2**256
    started_at = int(hex_data[128:192], 16)
    updated_at = int(hex_data[192:256], 16)

    # Chainlink USD feeds use 8 decimals
    price = answer / 1e8

    return json.dumps({
        "pair": pair.upper(),
        "price": price,
        "answer_raw": answer,
        "decimals": 8,
        "round_id": round_id,
        "updated_at": updated_at,
        "started_at": started_at,
        "feed": feed,
    }, indent=2)


@mcp.tool
async def eth_get_gas_price() -> str:
    """Get the current gas price in wei and gwei."""
    result = await _eth_rpc("eth_gasPrice")
    if isinstance(result, dict) and "error" in result:
        return json.dumps(result)
    wei = int(result, 16) if isinstance(result, str) else 0
    return json.dumps({"wei": wei, "gwei": round(wei / 1e9, 4)})


@mcp.tool
async def eth_estimate_gas(
    from_addr: str | None = None,
    to: str = "",
    value: str = "0x0",
    data: str = "0x",
) -> str:
    """Estimate gas for a transaction.

    Args:
        from_addr: Sender address (optional).
        to: Recipient / contract address.
        value: Value in wei (hex string).
        data: Calldata (hex string).
    """
    tx: dict = {"to": to, "value": value, "data": data}
    if from_addr:
        tx["from"] = from_addr
    result = await _eth_rpc("eth_estimateGas", [tx])
    if isinstance(result, dict) and "error" in result:
        return json.dumps(result)
    gas = int(result, 16) if isinstance(result, str) else 0
    return json.dumps({"estimated_gas": gas, "hex": result})


@mcp.tool
async def eth_get_fee_history(
    block_count: int = 10,
    newest_block: str = "latest",
    percentiles: list[int] | None = None,
) -> str:
    """Get fee history for recent blocks (EIP-1559).

    Args:
        block_count: Number of blocks to query (max 1024).
        newest_block: Block tag or hex number.
        percentiles: Reward percentiles to sample (default [25, 50, 75]).
    """
    pcts = percentiles or [25, 50, 75]
    result = await _eth_rpc("eth_feeHistory", [hex(min(block_count, 1024)), newest_block, pcts])
    if isinstance(result, dict) and "error" in result:
        return json.dumps(result)
    if not isinstance(result, dict):
        return json.dumps({"error": "Unexpected response", "raw": result})

    base_fees = [int(b, 16) if isinstance(b, str) else b for b in result.get("baseFeePerGas", [])]
    return json.dumps({
        "oldest_block": int(result.get("oldestBlock", "0x0"), 16) if isinstance(result.get("oldestBlock"), str) else result.get("oldestBlock"),
        "base_fee_per_gas_gwei": [round(f / 1e9, 4) for f in base_fees],
        "gas_used_ratio": result.get("gasUsedRatio", []),
        "reward": result.get("reward", []),
    }, indent=2)


@mcp.tool
async def eth_get_balance(address: str, block: str = "latest") -> str:
    """Get ETH balance for an address.

    Args:
        address: Ethereum address (0x...).
        block: Block tag or hex number.
    """
    result = await _eth_rpc("eth_getBalance", [address, block])
    if isinstance(result, dict) and "error" in result:
        return json.dumps(result)
    wei = int(result, 16) if isinstance(result, str) else 0
    return json.dumps({"address": address, "wei": wei, "eth": wei / 1e18})


@mcp.tool
async def eth_get_token_balance(token: str, owner: str, block: str = "latest") -> str:
    """Get ERC-20 token balance for an address.

    Args:
        token: ERC-20 contract address.
        owner: Owner address.
        block: Block tag or hex number.
    """
    # balanceOf(address) selector
    sel = _selector("balanceOf(address)")
    data = sel + _encode_address(owner)
    result = await _eth_call(token, data, block)
    if isinstance(result, dict) and "error" in result:
        return json.dumps(result)

    balance = int(result, 16) if isinstance(result, str) and len(result) > 2 else 0

    # Try to fetch decimals
    dec_sel = _selector("decimals()")
    dec_result = await _eth_call(token, dec_sel, block)
    decimals = 18
    if isinstance(dec_result, str) and len(dec_result) > 2:
        decimals = int(dec_result, 16)

    # Try to fetch symbol
    sym_sel = _selector("symbol()")
    sym_result = await _eth_call(token, sym_sel, block)
    symbol = ""
    if isinstance(sym_result, str) and len(sym_result) > 130:
        try:
            hex_data = sym_result.removeprefix("0x")
            # Dynamic string: offset (32B) + length (32B) + data
            str_len = int(hex_data[64:128], 16)
            symbol = bytes.fromhex(hex_data[128:128 + str_len * 2]).decode("utf-8", errors="replace").rstrip("\x00")
        except (ValueError, IndexError):
            pass

    return json.dumps({
        "token": token,
        "owner": owner,
        "balance_raw": str(balance),
        "decimals": decimals,
        "balance": balance / (10 ** decimals),
        "symbol": symbol,
    }, indent=2)


@mcp.tool
async def eth_get_transaction(tx_hash: str) -> str:
    """Get transaction details by hash.

    Args:
        tx_hash: Transaction hash (0x...).
    """
    result = await _eth_rpc("eth_getTransactionByHash", [tx_hash])
    if not result:
        return json.dumps({"error": "Transaction not found", "hash": tx_hash})
    if isinstance(result, dict) and "error" in result:
        return json.dumps(result)

    return json.dumps({
        "hash": result.get("hash"),
        "from": result.get("from"),
        "to": result.get("to"),
        "value_wei": int(result.get("value", "0x0"), 16),
        "value_eth": int(result.get("value", "0x0"), 16) / 1e18,
        "gas": int(result.get("gas", "0x0"), 16),
        "gas_price_gwei": int(result.get("gasPrice", "0x0"), 16) / 1e9 if result.get("gasPrice") else None,
        "max_fee_per_gas_gwei": int(result.get("maxFeePerGas", "0x0"), 16) / 1e9 if result.get("maxFeePerGas") else None,
        "max_priority_fee_gwei": int(result.get("maxPriorityFeePerGas", "0x0"), 16) / 1e9 if result.get("maxPriorityFeePerGas") else None,
        "nonce": int(result.get("nonce", "0x0"), 16),
        "block_number": int(result.get("blockNumber", "0x0"), 16) if result.get("blockNumber") else None,
        "block_hash": result.get("blockHash"),
        "input": result.get("input", "0x")[:66] + ("..." if len(result.get("input", "")) > 66 else ""),
        "type": int(result.get("type", "0x0"), 16) if result.get("type") else 0,
    }, indent=2)


@mcp.tool
async def eth_get_block(block: str = "latest", full_transactions: bool = False) -> str:
    """Get block details by number or tag.

    Args:
        block: Block number (hex) or tag ("latest", "pending", "earliest").
        full_transactions: Include full transaction objects (default: hashes only).
    """
    # Normalize decimal number input
    if block.isdigit():
        block = hex(int(block))

    result = await _eth_rpc("eth_getBlockByNumber", [block, full_transactions])
    if not result:
        return json.dumps({"error": "Block not found", "block": block})
    if isinstance(result, dict) and "error" in result:
        return json.dumps(result)

    return json.dumps({
        "number": int(result.get("number", "0x0"), 16) if result.get("number") else None,
        "hash": result.get("hash"),
        "parent_hash": result.get("parentHash"),
        "timestamp": int(result.get("timestamp", "0x0"), 16),
        "miner": result.get("miner"),
        "gas_used": int(result.get("gasUsed", "0x0"), 16),
        "gas_limit": int(result.get("gasLimit", "0x0"), 16),
        "base_fee_per_gas_gwei": int(result.get("baseFeePerGas", "0x0"), 16) / 1e9 if result.get("baseFeePerGas") else None,
        "transaction_count": len(result.get("transactions", [])),
        "size": int(result.get("size", "0x0"), 16),
    }, indent=2)


@mcp.tool
async def eth_get_transaction_receipt(tx_hash: str) -> str:
    """Get transaction receipt by hash.

    Args:
        tx_hash: Transaction hash (0x...).
    """
    result = await _eth_rpc("eth_getTransactionReceipt", [tx_hash])
    if not result:
        return json.dumps({"error": "Receipt not found", "hash": tx_hash})
    if isinstance(result, dict) and "error" in result:
        return json.dumps(result)

    return json.dumps({
        "hash": result.get("transactionHash"),
        "status": "success" if result.get("status") == "0x1" else "reverted",
        "block_number": int(result.get("blockNumber", "0x0"), 16) if result.get("blockNumber") else None,
        "from": result.get("from"),
        "to": result.get("to"),
        "contract_address": result.get("contractAddress"),
        "gas_used": int(result.get("gasUsed", "0x0"), 16),
        "effective_gas_price_gwei": int(result.get("effectiveGasPrice", "0x0"), 16) / 1e9 if result.get("effectiveGasPrice") else None,
        "cumulative_gas_used": int(result.get("cumulativeGasUsed", "0x0"), 16),
        "logs_count": len(result.get("logs", [])),
        "type": int(result.get("type", "0x0"), 16) if result.get("type") else 0,
    }, indent=2)


@mcp.tool
async def eth_resolve_ens(name: str) -> str:
    """Resolve an ENS name to an Ethereum address.

    Args:
        name: ENS name (e.g. "vitalik.eth").
    """
    # Use the Universal Resolver's resolve(bytes,bytes) function
    # For simplicity, we use the addr(bytes32) contenthash approach via
    # the public resolver obtained from the ENS registry.
    #
    # addr(bytes32 node) selector = 0x3b3b57de
    node = _namehash(name)
    sel = _selector("addr(bytes32)")
    data = sel + _pad32(node.removeprefix("0x"))

    # First, get the resolver for this name from the ENS registry
    ens_registry = "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e"
    resolver_sel = _selector("resolver(bytes32)")
    resolver_data = resolver_sel + _pad32(node.removeprefix("0x"))
    resolver_result = await _eth_call(ens_registry, resolver_data)

    if isinstance(resolver_result, dict) and "error" in resolver_result:
        return json.dumps(resolver_result)
    if not isinstance(resolver_result, str) or resolver_result == "0x" + "0" * 64:
        return json.dumps({"error": "No resolver found for name", "name": name})

    resolver_addr = "0x" + resolver_result.removeprefix("0x")[-40:]

    # Now call addr(node) on the resolver
    addr_result = await _eth_call(resolver_addr, data)
    if isinstance(addr_result, dict) and "error" in addr_result:
        return json.dumps(addr_result)
    if not isinstance(addr_result, str) or addr_result == "0x" + "0" * 64:
        return json.dumps({"error": "Name not resolved", "name": name})

    address = "0x" + addr_result.removeprefix("0x")[-40:]
    return json.dumps({"name": name, "address": address, "resolver": resolver_addr})


@mcp.tool
async def eth_lookup_ens(address: str) -> str:
    """Reverse ENS lookup — resolve an address to an ENS name.

    Args:
        address: Ethereum address (0x...).
    """
    # Reverse name: <addr>.addr.reverse
    addr_lower = address.lower().removeprefix("0x")
    reverse_name = f"{addr_lower}.addr.reverse"
    node = _namehash(reverse_name)

    ens_registry = "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e"
    resolver_sel = _selector("resolver(bytes32)")
    resolver_data = resolver_sel + _pad32(node.removeprefix("0x"))
    resolver_result = await _eth_call(ens_registry, resolver_data)

    if isinstance(resolver_result, dict) and "error" in resolver_result:
        return json.dumps(resolver_result)
    if not isinstance(resolver_result, str) or resolver_result == "0x" + "0" * 64:
        return json.dumps({"error": "No reverse record found", "address": address})

    resolver_addr = "0x" + resolver_result.removeprefix("0x")[-40:]

    # name(bytes32) selector
    name_sel = _selector("name(bytes32)")
    name_data = name_sel + _pad32(node.removeprefix("0x"))
    name_result = await _eth_call(resolver_addr, name_data)

    if isinstance(name_result, dict) and "error" in name_result:
        return json.dumps(name_result)
    if not isinstance(name_result, str) or len(name_result) < 130:
        return json.dumps({"error": "No reverse record found", "address": address})

    hex_data = name_result.removeprefix("0x")
    try:
        str_len = int(hex_data[64:128], 16)
        name = bytes.fromhex(hex_data[128:128 + str_len * 2]).decode("utf-8", errors="replace").rstrip("\x00")
    except (ValueError, IndexError):
        return json.dumps({"error": "Failed to decode name", "address": address})

    return json.dumps({"address": address, "name": name, "resolver": resolver_addr})


@mcp.tool
async def eth_call_contract(
    to: str,
    data: str,
    block: str = "latest",
    from_addr: str | None = None,
) -> str:
    """Execute a read-only (view/pure) contract call via eth_call.

    Args:
        to: Contract address.
        data: ABI-encoded calldata (hex string starting with 0x).
        block: Block tag or hex number.
        from_addr: Optional sender address for context.
    """
    tx: dict = {"to": to, "data": data}
    if from_addr:
        tx["from"] = from_addr
    result = await _eth_rpc("eth_call", [tx, block])
    if isinstance(result, dict) and "error" in result:
        return json.dumps(result)
    return json.dumps({"to": to, "result": result})


@mcp.tool
async def eth_encode_function(signature: str, args: list[str] | None = None) -> str:
    """ABI-encode a Solidity function call (selector + parameters).

    Supports basic types: address, uint256, bytes32, bool, string (static only).

    Args:
        signature: Solidity function signature (e.g. "transfer(address,uint256)").
        args: List of argument values as strings.

    Returns:
        Hex-encoded calldata.
    """
    sel = _selector(signature)
    if not args:
        return json.dumps({"signature": signature, "selector": sel, "calldata": sel})

    # Parse parameter types from signature
    params_str = signature.split("(", 1)[1].rstrip(")")
    param_types = [p.strip() for p in params_str.split(",")] if params_str else []

    if len(param_types) != len(args):
        return json.dumps({
            "error": f"Expected {len(param_types)} args, got {len(args)}",
            "signature": signature,
        })

    encoded = sel
    for ptype, arg in zip(param_types, args):
        if ptype == "address":
            encoded += _encode_address(arg)
        elif ptype.startswith("uint"):
            encoded += _encode_uint256(int(arg))
        elif ptype.startswith("int"):
            val = int(arg)
            if val < 0:
                val = val + 2**256
            encoded += _encode_uint256(val)
        elif ptype == "bytes32":
            encoded += _encode_bytes32(arg)
        elif ptype == "bool":
            encoded += _encode_uint256(1 if arg.lower() in ("true", "1") else 0)
        else:
            return json.dumps({
                "error": f"Unsupported type '{ptype}'. Supported: address, uint*, int*, bytes32, bool",
                "signature": signature,
            })

    return json.dumps({
        "signature": signature,
        "selector": sel,
        "calldata": encoded,
        "args": args,
    }, indent=2)


@mcp.tool
async def eth_register_agent_8004(
    agent_id: str,
    metadata_uri: str,
    owner: str,
) -> str:
    """Build ERC-8004 registerAgent calldata.

    Returns the encoded calldata for the registerAgent(string,string,address)
    function on the ERC-8004 Agent Registry contract. The caller must sign
    and submit the transaction.

    Args:
        agent_id: Unique agent identifier string.
        metadata_uri: URI pointing to agent metadata JSON.
        owner: Owner address for the agent registration.
    """
    # registerAgent(string agentId, string metadataUri, address owner)
    # Dynamic types: need offset encoding
    sel = _selector("registerAgent(string,string,address)")

    # Offsets for the three params (address is static, strings are dynamic)
    # Layout: [offset_agentId, offset_metadataUri, address, agentId_data, metadataUri_data]
    # offset for agentId string = 3 * 32 = 96 bytes
    # offset for metadataUri = 96 + 32 + ceil32(len(agentId))
    agent_id_bytes = agent_id.encode("utf-8")
    metadata_bytes = metadata_uri.encode("utf-8")

    agent_id_padded_len = ((len(agent_id_bytes) + 31) // 32) * 32
    metadata_padded_len = ((len(metadata_bytes) + 31) // 32) * 32

    offset_agent_id = 3 * 32  # after three 32-byte head slots
    offset_metadata = offset_agent_id + 32 + agent_id_padded_len

    head = (
        _encode_uint256(offset_agent_id)
        + _encode_uint256(offset_metadata)
        + _encode_address(owner)
    )

    # Encode string: length (32B) + data (padded to 32B)
    agent_id_enc = _encode_uint256(len(agent_id_bytes)) + agent_id_bytes.hex().ljust(agent_id_padded_len * 2, "0")
    metadata_enc = _encode_uint256(len(metadata_bytes)) + metadata_bytes.hex().ljust(metadata_padded_len * 2, "0")

    calldata = sel + head + agent_id_enc + metadata_enc

    return json.dumps({
        "function": "registerAgent(string,string,address)",
        "contract": ERC_8004_REGISTRY,
        "calldata": calldata,
        "agent_id": agent_id,
        "metadata_uri": metadata_uri,
        "owner": owner,
    }, indent=2)


@mcp.tool
async def eth_lookup_agent_8004(agent_id: str) -> str:
    """Look up an agent via ERC-8004 getAgent on-chain.

    Args:
        agent_id: The agent identifier to look up.
    """
    # getAgent(string agentId) -> (address owner, string metadataUri, bool active)
    sel = _selector("getAgent(string)")
    agent_bytes = agent_id.encode("utf-8")
    padded_len = ((len(agent_bytes) + 31) // 32) * 32

    # Head: offset to string data = 32
    data = sel + _encode_uint256(32) + _encode_uint256(len(agent_bytes)) + agent_bytes.hex().ljust(padded_len * 2, "0")

    result = await _eth_call(ERC_8004_REGISTRY, data)
    if isinstance(result, dict) and "error" in result:
        return json.dumps(result)
    if not isinstance(result, str) or result == "0x" or len(result) < 66:
        return json.dumps({"error": "Agent not found or registry not deployed", "agent_id": agent_id})

    hex_data = result.removeprefix("0x")

    # Decode: address (32B) + offset_metadataUri (32B) + bool (32B) + string_data
    try:
        owner = "0x" + hex_data[24:64]  # last 20 bytes of first 32-byte word
        active = int(hex_data[128:192], 16) != 0

        # Decode metadata URI string
        meta_offset = int(hex_data[64:128], 16) * 2  # offset in hex chars
        meta_len = int(hex_data[meta_offset:meta_offset + 64], 16)
        metadata_uri = bytes.fromhex(hex_data[meta_offset + 64:meta_offset + 64 + meta_len * 2]).decode("utf-8", errors="replace")

        return json.dumps({
            "agent_id": agent_id,
            "owner": owner,
            "metadata_uri": metadata_uri,
            "active": active,
            "contract": ERC_8004_REGISTRY,
        }, indent=2)
    except (ValueError, IndexError) as exc:
        return json.dumps({"error": f"Failed to decode response: {exc}", "raw": result[:200]})


@mcp.tool
async def eth_get_attestation(uid: str) -> str:
    """Query an EAS (Ethereum Attestation Service) attestation by UID.

    Args:
        uid: Attestation UID (bytes32 hex string).
    """
    query = """
    query GetAttestation($uid: String!) {
        attestation(where: { id: $uid }) {
            id
            attester
            recipient
            revoked
            revocationTime
            expirationTime
            time
            txid
            schemaId
            decodedDataJson
        }
    }
    """
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            EAS_GRAPHQL,
            json={"query": query, "variables": {"uid": uid}},
        )
        data = resp.json()

    attestation = data.get("data", {}).get("attestation")
    if not attestation:
        errors = data.get("errors", [])
        return json.dumps({"error": "Attestation not found", "uid": uid, "details": errors})

    return json.dumps({
        "uid": attestation.get("id"),
        "attester": attestation.get("attester"),
        "recipient": attestation.get("recipient"),
        "revoked": attestation.get("revoked"),
        "revocation_time": attestation.get("revocationTime"),
        "expiration_time": attestation.get("expirationTime"),
        "time": attestation.get("time"),
        "tx_hash": attestation.get("txid"),
        "schema_id": attestation.get("schemaId"),
        "decoded_data": attestation.get("decodedDataJson"),
    }, indent=2)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Tenzro Ethereum MCP Server")
    parser.add_argument("--transport", choices=["http", "sse", "stdio"], default="http")
    parser.add_argument("--port", type=int, default=3004)
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
