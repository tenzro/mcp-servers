"""Tenzro Chainlink MCP Server — 20 tools for Chainlink CCIP, data feeds, VRF, Automation, and Functions."""

import json
import os
from typing import Any

import httpx
from eth_abi import encode, decode
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tenzro-chainlink-mcp")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ETHEREUM_RPC_URL = os.environ.get("ETHEREUM_RPC_URL", "https://eth.llamarpc.com")
DATA_STREAMS_API = os.environ.get("CHAINLINK_DATA_STREAMS_API", "https://api.chainlink-data-streams.io")

# Ethereum mainnet addresses
CCIP_ROUTER = "0x80226fc0Ee2b096224EeAc085Bb9a8cba1146f7D"
VRF_COORDINATOR_V25 = "0xD7f86b4b8Cae7D942340FF628F82735b7a20893a"
AUTOMATION_REGISTRY_V21 = "0x6593c7De001fC8542bB1703532EE1E5aA0D458fD"
FUNCTIONS_ROUTER = "0x65Dcc24F8ff9e51F10DCc7Ed1e4e2A61e6E14bd6"

# Well-known Chainlink price feeds (Ethereum mainnet)
PRICE_FEEDS: dict[str, dict[str, Any]] = {
    "ETH/USD":  {"address": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419", "decimals": 8},
    "BTC/USD":  {"address": "0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c", "decimals": 8},
    "LINK/USD": {"address": "0x2c1d072e956AFFC0D435Cb7AC38EF18d24d9127c", "decimals": 8},
    "USDC/USD": {"address": "0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6", "decimals": 8},
    "USDT/USD": {"address": "0x3E7d1eAB13ad0104d2750B8863b489D65364e32D", "decimals": 8},
    "DAI/USD":  {"address": "0xAed0c38402a5d19df6E4c03F4E2DceD6e29c1ee9", "decimals": 8},
    "SOL/USD":  {"address": "0x4ffC43a60e009B551865A93d232E33Fce9f01507", "decimals": 8},
    "AVAX/USD": {"address": "0xFF3EEb22B5E3dE6e705b44749C2559d704923FD7", "decimals": 8},
    "MATIC/USD": {"address": "0x7bAC85A8a13A4BcD8abb3eB7d6b4d632c5a57676", "decimals": 8},
    "ARB/USD":  {"address": "0x31697852a68433DbCc2Ff9bA924722580E9914bB", "decimals": 8},
}

# CCIP chain selectors (Chainlink-specific, NOT standard chain IDs)
CCIP_CHAINS: dict[str, dict[str, Any]] = {
    "ethereum":        {"selector": "5009297550715157269",  "chain_id": 1,     "router": CCIP_ROUTER},
    "arbitrum":        {"selector": "4949039107694359620",  "chain_id": 42161, "router": "0x141fa059441E0ca23ce184B6A78bafD2A517DdE8"},
    "optimism":        {"selector": "3734403246176062136",  "chain_id": 10,    "router": "0x3206695CaE29952f4b0c22a169725a865bc8Ce0f"},
    "polygon":         {"selector": "4051577828743386545",  "chain_id": 137,   "router": "0x849c5ED5a80F5B408Dd4969b78c2C8fdf0565Bce"},
    "avalanche":       {"selector": "6433500567565415381",  "chain_id": 43114, "router": "0xF4c7E640EdA248ef95972845a62bdC74237805dB"},
    "bsc":             {"selector": "11344663589394136015", "chain_id": 56,    "router": "0x34B03Cb9086d7D758AC55af71584F81A598759FE"},
    "base":            {"selector": "15971525489660198786", "chain_id": 8453,  "router": "0x881e3A65B4d4a04310c4505f1d9e2a9604Fb6415"},
}

# CCIP supported tokens per chain
CCIP_TOKENS = {
    "ethereum": ["LINK", "WETH", "USDC", "USDT", "WBTC"],
    "arbitrum": ["LINK", "WETH", "USDC", "USDT"],
    "optimism": ["LINK", "WETH", "USDC"],
    "polygon":  ["LINK", "WMATIC", "USDC", "USDT"],
    "base":     ["LINK", "WETH", "USDC"],
}

# Proof of Reserve feeds
POR_FEEDS: dict[str, dict[str, Any]] = {
    "WBTC":  {"address": "0xa81FE04086865e63E12dD3776978E49DEEb93CA8", "decimals": 8, "asset": "Bitcoin"},
    "USDC":  {"address": "0x09023c0DA49Aaf8fc3fA3ADF34C6A7016D38D5e3", "decimals": 18, "asset": "USDC Reserves"},
    "TUSD":  {"address": "0x478F4c42b877c697C4b19E396865D4D533EcB6ea", "decimals": 18, "asset": "TrueUSD"},
}

# Data Streams well-known feeds
DS_FEEDS = [
    {"id": "ETH-USD-CRYPTO-MAINNET", "name": "ETH/USD", "category": "crypto"},
    {"id": "BTC-USD-CRYPTO-MAINNET", "name": "BTC/USD", "category": "crypto"},
    {"id": "LINK-USD-CRYPTO-MAINNET", "name": "LINK/USD", "category": "crypto"},
    {"id": "SOL-USD-CRYPTO-MAINNET", "name": "SOL/USD", "category": "crypto"},
    {"id": "EUR-USD-FOREX-MAINNET", "name": "EUR/USD", "category": "forex"},
    {"id": "GBP-USD-FOREX-MAINNET", "name": "GBP/USD", "category": "forex"},
]

_http = httpx.AsyncClient(timeout=30)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _eth_call(rpc_url: str, to: str, data: str) -> str:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_call",
        "params": [{"to": to, "data": data}, "latest"],
    }
    resp = await _http.post(rpc_url, json=payload)
    result = resp.json()
    if "error" in result:
        raise ValueError(f"RPC error: {result['error']}")
    return result["result"]


def _pad32(b: bytes) -> bytes:
    return b.rjust(32, b"\x00")


# ---------------------------------------------------------------------------
# Tools — Price Feeds
# ---------------------------------------------------------------------------

@mcp.tool()
async def chainlink_get_price(pair: str, rpc_url: str | None = None) -> dict:
    """Get the latest price from a Chainlink AggregatorV3 feed via latestRoundData().

    Args:
        pair: Price pair (e.g. "ETH/USD", "BTC/USD") or direct feed address
        rpc_url: Optional RPC URL (defaults to Ethereum mainnet)
    """
    rpc = rpc_url or ETHEREUM_RPC_URL

    if pair.startswith("0x"):
        feed_address = pair
        decimals = 8
        pair_name = pair
    else:
        feed = PRICE_FEEDS.get(pair.upper())
        if not feed:
            return {"error": f"Unknown feed: {pair}. Known: {', '.join(PRICE_FEEDS.keys())}"}
        feed_address = feed["address"]
        decimals = feed["decimals"]
        pair_name = pair.upper()

    # latestRoundData() selector: 0xfeaf968c
    result_hex = await _eth_call(rpc, feed_address, "0xfeaf968c")
    data = bytes.fromhex(result_hex.replace("0x", ""))

    # Returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound)
    round_id = int.from_bytes(data[0:32], "big")
    answer = int.from_bytes(data[32:64], "big", signed=True)
    started_at = int.from_bytes(data[64:96], "big")
    updated_at = int.from_bytes(data[96:128], "big")
    answered_in_round = int.from_bytes(data[128:160], "big")

    price = answer / (10 ** decimals)

    return {
        "pair": pair_name,
        "price": price,
        "raw_answer": str(answer),
        "decimals": decimals,
        "round_id": str(round_id),
        "updated_at": updated_at,
        "feed_address": feed_address,
    }


@mcp.tool()
async def chainlink_list_feeds() -> dict:
    """List known Chainlink price feed addresses on Ethereum mainnet."""
    feeds = []
    for pair, info in PRICE_FEEDS.items():
        feeds.append({
            "pair": pair,
            "address": info["address"],
            "decimals": info["decimals"],
        })
    return {"feeds": feeds, "count": len(feeds), "network": "ethereum_mainnet"}


# ---------------------------------------------------------------------------
# Tools — CCIP
# ---------------------------------------------------------------------------

@mcp.tool()
async def ccip_get_fee(
    src_chain: str,
    dst_chain: str,
    receiver: str,
    data: str = "0x",
    token_amounts: list[dict] | None = None,
    rpc_url: str | None = None,
) -> dict:
    """Quote CCIP cross-chain message fee via Router.getFee().

    Args:
        src_chain: Source chain name (e.g. "ethereum")
        dst_chain: Destination chain name
        receiver: Receiver address on destination chain
        data: Hex-encoded message data (default empty)
        token_amounts: Optional list of {token, amount} to transfer
        rpc_url: Optional source chain RPC URL
    """
    src = CCIP_CHAINS.get(src_chain.lower())
    dst = CCIP_CHAINS.get(dst_chain.lower())
    if not src:
        return {"error": f"Unknown source chain: {src_chain}. Supported: {', '.join(CCIP_CHAINS.keys())}"}
    if not dst:
        return {"error": f"Unknown destination chain: {dst_chain}. Supported: {', '.join(CCIP_CHAINS.keys())}"}

    rpc = rpc_url or ETHEREUM_RPC_URL
    dst_selector = int(dst["selector"])

    msg_data = bytes.fromhex(data.replace("0x", "")) if data != "0x" else b""
    receiver_bytes = bytes.fromhex(receiver.replace("0x", ""))

    # Encode EVM2AnyMessage: (bytes receiver, bytes data, EVMTokenAmount[] tokenAmounts, address feeToken, bytes extraArgs)
    token_tuples = []
    if token_amounts:
        for ta in token_amounts:
            token_tuples.append((ta["token"], int(ta["amount"])))

    # Use allowOutOfOrderExecution = true (GenericExtraArgsV2)
    extra_args_tag = bytes.fromhex("181dcf10")
    gas_limit_bytes = (200_000).to_bytes(32, "big")
    allow_ooo = b"\x00" * 31 + b"\x01"
    extra_args = extra_args_tag + gas_limit_bytes + allow_ooo

    # getFee(uint64 destinationChainSelector, EVM2AnyMessage message)
    # EVM2AnyMessage = (bytes, bytes, (address,uint256)[], address, bytes)
    evm2any = encode(
        ["uint64", "(bytes,bytes,(address,uint256)[],address,bytes)"],
        [
            dst_selector,
            (
                receiver_bytes,
                msg_data,
                token_tuples,
                "0x0000000000000000000000000000000000000000",  # native fee
                extra_args,
            ),
        ],
    )
    # getFee selector: 0x20487ded
    calldata = "0x20487ded" + evm2any.hex()

    result_hex = await _eth_call(rpc, src["router"], calldata)
    fee = int(result_hex, 16)

    return {
        "fee_wei": str(fee),
        "fee_eth": f"{fee / 1e18:.8f}",
        "src_chain": src_chain,
        "dst_chain": dst_chain,
        "dst_selector": str(dst_selector),
        "router": src["router"],
    }


@mcp.tool()
async def ccip_send_message(
    src_chain: str,
    dst_chain: str,
    sender: str,
    receiver: str,
    data: str = "0x",
    token_amounts: list[dict] | None = None,
    fee_wei: str | None = None,
) -> dict:
    """Build Router.ccipSend() calldata for a CCIP cross-chain message.

    Returns calldata and value. Does NOT broadcast.

    Args:
        src_chain: Source chain name
        dst_chain: Destination chain name
        sender: Sender address
        receiver: Receiver address on destination
        data: Hex-encoded message data
        token_amounts: Optional list of {token, amount}
        fee_wei: Fee in wei (if None, quotes automatically)
    """
    src = CCIP_CHAINS.get(src_chain.lower())
    dst = CCIP_CHAINS.get(dst_chain.lower())
    if not src or not dst:
        return {"error": f"Unsupported chain pair: {src_chain} -> {dst_chain}"}

    if fee_wei is None:
        quote = await ccip_get_fee(src_chain, dst_chain, receiver, data, token_amounts)
        if "error" in quote:
            return quote
        fee = int(quote["fee_wei"])
    else:
        fee = int(fee_wei)

    dst_selector = int(dst["selector"])
    msg_data = bytes.fromhex(data.replace("0x", "")) if data != "0x" else b""
    receiver_bytes = bytes.fromhex(receiver.replace("0x", ""))

    token_tuples = []
    if token_amounts:
        for ta in token_amounts:
            token_tuples.append((ta["token"], int(ta["amount"])))

    extra_args_tag = bytes.fromhex("181dcf10")
    gas_limit_bytes = (200_000).to_bytes(32, "big")
    allow_ooo = b"\x00" * 31 + b"\x01"
    extra_args = extra_args_tag + gas_limit_bytes + allow_ooo

    # ccipSend(uint64, EVM2AnyMessage)
    params = encode(
        ["uint64", "(bytes,bytes,(address,uint256)[],address,bytes)"],
        [
            dst_selector,
            (
                receiver_bytes,
                msg_data,
                token_tuples,
                "0x0000000000000000000000000000000000000000",
                extra_args,
            ),
        ],
    )
    # ccipSend selector: 0x96f4e9f9
    calldata = "0x96f4e9f9" + params.hex()

    return {
        "to": src["router"],
        "calldata": calldata,
        "value_wei": str(fee),
        "src_chain": src_chain,
        "dst_chain": dst_chain,
        "description": f"CCIP send from {src_chain} to {dst_chain}",
    }


@mcp.tool()
async def ccip_track_message(
    message_id: str,
    dst_chain: str,
    off_ramp: str,
    rpc_url: str | None = None,
) -> dict:
    """Track CCIP message execution state via OffRamp.getExecutionState().

    Args:
        message_id: CCIP message ID (bytes32 hex)
        dst_chain: Destination chain name
        off_ramp: OffRamp contract address on destination chain
        rpc_url: Optional destination chain RPC URL
    """
    dst = CCIP_CHAINS.get(dst_chain.lower())
    if not dst:
        return {"error": f"Unknown chain: {dst_chain}"}

    rpc = rpc_url or ETHEREUM_RPC_URL
    msg_id_bytes = bytes.fromhex(message_id.replace("0x", ""))
    params = encode(["uint64", "bytes32"], [0, msg_id_bytes])
    # getExecutionState selector: 0x142a714c
    calldata = "0x142a714c" + params.hex()

    result_hex = await _eth_call(rpc, off_ramp, calldata)
    state = int(result_hex, 16)

    state_names = {0: "UNTOUCHED", 1: "IN_PROGRESS", 2: "SUCCESS", 3: "FAILURE"}

    return {
        "message_id": message_id,
        "execution_state": state,
        "state_name": state_names.get(state, "UNKNOWN"),
        "dst_chain": dst_chain,
        "off_ramp": off_ramp,
    }


@mcp.tool()
async def ccip_get_supported_chains() -> dict:
    """List CCIP chain selectors and router addresses."""
    chains = []
    for name, info in CCIP_CHAINS.items():
        chains.append({
            "name": name,
            "chain_id": info["chain_id"],
            "selector": info["selector"],
            "router": info["router"],
        })
    return {"chains": chains, "count": len(chains)}


@mcp.tool()
async def ccip_get_supported_tokens(chain: str) -> dict:
    """List supported tokens for a CCIP chain.

    Args:
        chain: Chain name (e.g. "ethereum", "arbitrum")
    """
    tokens = CCIP_TOKENS.get(chain.lower())
    if tokens is None:
        return {"error": f"Unknown chain: {chain}", "supported": list(CCIP_TOKENS.keys())}
    return {"chain": chain, "tokens": tokens, "count": len(tokens)}


@mcp.tool()
async def ccip_get_lanes() -> dict:
    """List available CCIP lanes (chain pairs)."""
    chains = list(CCIP_CHAINS.keys())
    lanes = []
    for src in chains:
        for dst in chains:
            if src != dst:
                lanes.append({"src": src, "dst": dst})
    return {"lanes": lanes, "count": len(lanes)}


@mcp.tool()
async def ccip_get_token_pool(
    token: str,
    chain: str = "ethereum",
    pool_address: str | None = None,
    rpc_url: str | None = None,
) -> dict:
    """Get CCT v1.6+ token pool info.

    Args:
        token: Token symbol
        chain: Chain name (default ethereum)
        pool_address: Token pool contract address (required for on-chain query)
        rpc_url: Optional RPC URL
    """
    if not pool_address:
        return {
            "token": token,
            "chain": chain,
            "note": "Provide pool_address to query on-chain pool info. Pool addresses vary by deployment.",
        }

    rpc = rpc_url or ETHEREUM_RPC_URL
    # getToken() selector: 0x21df0da7
    result_hex = await _eth_call(rpc, pool_address, "0x21df0da7")
    token_addr = "0x" + result_hex[-40:]

    return {
        "token": token,
        "chain": chain,
        "pool_address": pool_address,
        "token_address": token_addr,
        "pool_version": "CCT v1.6+",
    }


@mcp.tool()
async def ccip_get_rate_limits(
    chain: str = "ethereum",
    on_ramp: str | None = None,
    dst_chain: str | None = None,
    rpc_url: str | None = None,
) -> dict:
    """Get per-lane rate limiter configuration from a CCIP OnRamp.

    Args:
        chain: Source chain name
        on_ramp: OnRamp contract address (required for on-chain query)
        dst_chain: Destination chain name for context
        rpc_url: Optional RPC URL
    """
    if not on_ramp:
        return {
            "chain": chain,
            "note": "Provide on_ramp address to query rate limits. OnRamp addresses vary by lane.",
        }

    rpc = rpc_url or ETHEREUM_RPC_URL
    # currentRateLimiterState() selector: 0x546719cd
    result_hex = await _eth_call(rpc, on_ramp, "0x546719cd")
    data = bytes.fromhex(result_hex.replace("0x", ""))

    tokens = int.from_bytes(data[0:32], "big")
    last_updated = int.from_bytes(data[32:64], "big")
    is_enabled = int.from_bytes(data[64:96], "big") != 0
    capacity = int.from_bytes(data[96:128], "big")
    rate = int.from_bytes(data[128:160], "big")

    return {
        "chain": chain,
        "dst_chain": dst_chain,
        "on_ramp": on_ramp,
        "enabled": is_enabled,
        "tokens_available": str(tokens),
        "capacity": str(capacity),
        "rate": str(rate),
        "last_updated": last_updated,
    }


# ---------------------------------------------------------------------------
# Tools — Data Streams
# ---------------------------------------------------------------------------

@mcp.tool()
async def ds_get_report(feed_id: str) -> dict:
    """Get a Data Streams report for sub-second market data.

    Args:
        feed_id: Data Streams feed ID (e.g. "ETH-USD-CRYPTO-MAINNET")
    """
    url = f"{DATA_STREAMS_API}/api/v1/reports"
    resp = await _http.get(url, params={"feedID": feed_id})
    if resp.status_code == 401:
        return {"error": "Data Streams API requires authentication. Set credentials via environment."}
    if resp.status_code == 404:
        return {"error": f"Feed not found: {feed_id}"}
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
async def ds_list_feeds() -> dict:
    """List available Chainlink Data Streams feeds (crypto, forex, equities, commodities)."""
    return {"feeds": DS_FEEDS, "count": len(DS_FEEDS)}


# ---------------------------------------------------------------------------
# Tools — VRF v2.5
# ---------------------------------------------------------------------------

@mcp.tool()
async def vrf_request_random(
    subscription_id: int,
    key_hash: str,
    num_words: int = 1,
    confirmations: int = 3,
    callback_gas_limit: int = 100_000,
    native_payment: bool = False,
) -> dict:
    """Build VRF v2.5 requestRandomWords() calldata.

    Args:
        subscription_id: VRF subscription ID
        key_hash: Key hash for the VRF provider
        num_words: Number of random words (1-500)
        confirmations: Request confirmations (3-200)
        callback_gas_limit: Gas limit for fulfillment callback
        native_payment: Pay with native token instead of LINK
    """
    key_hash_bytes = bytes.fromhex(key_hash.replace("0x", ""))
    # requestRandomWords(bytes32,uint64,uint16,uint32,uint32,bool) for v2.5
    params = encode(
        ["bytes32", "uint256", "uint16", "uint32", "uint32", "bool"],
        [key_hash_bytes, subscription_id, confirmations, callback_gas_limit, num_words, native_payment],
    )
    # requestRandomWords selector for v2.5
    calldata = "0x9b1c385e" + params.hex()

    return {
        "to": VRF_COORDINATOR_V25,
        "calldata": "0x" + calldata,
        "value_wei": "0",
        "subscription_id": subscription_id,
        "num_words": num_words,
        "native_payment": native_payment,
        "description": f"VRF v2.5 requestRandomWords for {num_words} word(s)",
    }


@mcp.tool()
async def vrf_get_subscription(
    subscription_id: int,
    rpc_url: str | None = None,
) -> dict:
    """Get VRF v2.5 subscription info (balance, consumers).

    Args:
        subscription_id: VRF subscription ID
        rpc_url: Optional RPC URL
    """
    rpc = rpc_url or ETHEREUM_RPC_URL
    params = encode(["uint256"], [subscription_id])
    # getSubscription selector: 0xa47c7696
    calldata = "0xa47c7696" + params.hex()

    result_hex = await _eth_call(rpc, VRF_COORDINATOR_V25, calldata)
    data = bytes.fromhex(result_hex.replace("0x", ""))

    balance = int.from_bytes(data[0:32], "big")
    native_balance = int.from_bytes(data[32:64], "big")
    req_count = int.from_bytes(data[64:96], "big")
    owner = "0x" + data[96:128][-20:].hex()

    return {
        "subscription_id": subscription_id,
        "balance_link": f"{balance / 1e18:.6f}",
        "balance_native_wei": str(native_balance),
        "request_count": req_count,
        "owner": owner,
        "coordinator": VRF_COORDINATOR_V25,
    }


# ---------------------------------------------------------------------------
# Tools — Proof of Reserve
# ---------------------------------------------------------------------------

@mcp.tool()
async def por_get_reserve(
    asset: str,
    rpc_url: str | None = None,
) -> dict:
    """Read a Proof of Reserve feed value.

    Args:
        asset: Asset name (e.g. "WBTC", "USDC", "TUSD") or feed address
        rpc_url: Optional RPC URL
    """
    rpc = rpc_url or ETHEREUM_RPC_URL

    if asset.startswith("0x"):
        feed_address = asset
        decimals = 8
        asset_name = asset
    else:
        feed = POR_FEEDS.get(asset.upper())
        if not feed:
            return {"error": f"Unknown PoR feed: {asset}. Known: {', '.join(POR_FEEDS.keys())}"}
        feed_address = feed["address"]
        decimals = feed["decimals"]
        asset_name = feed["asset"]

    result_hex = await _eth_call(rpc, feed_address, "0xfeaf968c")
    data = bytes.fromhex(result_hex.replace("0x", ""))

    answer = int.from_bytes(data[32:64], "big", signed=True)
    updated_at = int.from_bytes(data[96:128], "big")
    reserve = answer / (10 ** decimals)

    return {
        "asset": asset_name,
        "reserve": reserve,
        "raw_answer": str(answer),
        "decimals": decimals,
        "updated_at": updated_at,
        "feed_address": feed_address,
    }


@mcp.tool()
async def por_list_feeds() -> dict:
    """List known Proof of Reserve feeds."""
    feeds = []
    for key, info in POR_FEEDS.items():
        feeds.append({
            "symbol": key,
            "asset": info["asset"],
            "address": info["address"],
            "decimals": info["decimals"],
        })
    return {"feeds": feeds, "count": len(feeds)}


# ---------------------------------------------------------------------------
# Tools — Automation
# ---------------------------------------------------------------------------

@mcp.tool()
async def chainlink_check_upkeep(
    upkeep_id: str,
    registry: str | None = None,
    rpc_url: str | None = None,
) -> dict:
    """Dry-run Automation checkUpkeep() to see if upkeep is needed.

    Args:
        upkeep_id: Upkeep ID (uint256)
        registry: Automation Registry address (defaults to v2.1 on Ethereum)
        rpc_url: Optional RPC URL
    """
    rpc = rpc_url or ETHEREUM_RPC_URL
    reg = registry or AUTOMATION_REGISTRY_V21

    params = encode(["uint256", "bytes"], [int(upkeep_id), b""])
    # checkUpkeep(uint256,bytes) selector
    calldata = "0xf7d334ba" + params.hex()

    try:
        result_hex = await _eth_call(rpc, reg, calldata)
        data = bytes.fromhex(result_hex.replace("0x", ""))
        upkeep_needed = int.from_bytes(data[0:32], "big") != 0
        return {
            "upkeep_id": upkeep_id,
            "upkeep_needed": upkeep_needed,
            "registry": reg,
        }
    except ValueError as e:
        return {"upkeep_id": upkeep_id, "error": str(e), "registry": reg}


@mcp.tool()
async def chainlink_get_upkeep_info(
    upkeep_id: str,
    registry: str | None = None,
    rpc_url: str | None = None,
) -> dict:
    """Get Automation upkeep info from the registry.

    Args:
        upkeep_id: Upkeep ID (uint256)
        registry: Automation Registry address (defaults to v2.1 on Ethereum)
        rpc_url: Optional RPC URL
    """
    rpc = rpc_url or ETHEREUM_RPC_URL
    reg = registry or AUTOMATION_REGISTRY_V21

    params = encode(["uint256"], [int(upkeep_id)])
    # getUpkeep(uint256) selector: 0xc7c3a19a
    calldata = "0xc7c3a19a" + params.hex()

    try:
        result_hex = await _eth_call(rpc, reg, calldata)
        data = bytes.fromhex(result_hex.replace("0x", ""))
        target = "0x" + data[0:32][-20:].hex()
        balance = int.from_bytes(data[32:64], "big")
        gas_limit = int.from_bytes(data[128:160], "big")

        return {
            "upkeep_id": upkeep_id,
            "target": target,
            "balance_link": f"{balance / 1e18:.6f}",
            "gas_limit": gas_limit,
            "registry": reg,
        }
    except ValueError as e:
        return {"upkeep_id": upkeep_id, "error": str(e), "registry": reg}


# ---------------------------------------------------------------------------
# Tools — Functions
# ---------------------------------------------------------------------------

@mcp.tool()
async def chainlink_estimate_functions_cost(
    callback_gas_limit: int = 300_000,
    gas_price_gwei: float = 20.0,
    don_fee_juels: int = 200_000_000_000_000_000,
) -> dict:
    """Estimate the cost of a Chainlink Functions DON execution.

    Args:
        callback_gas_limit: Gas limit for the callback function
        gas_price_gwei: Current gas price in gwei
        don_fee_juels: DON premium fee in juels (1 LINK = 1e18 juels)
    """
    gas_cost_wei = callback_gas_limit * int(gas_price_gwei * 1e9)
    gas_cost_eth = gas_cost_wei / 1e18
    don_fee_link = don_fee_juels / 1e18

    return {
        "callback_gas_limit": callback_gas_limit,
        "gas_cost_eth": f"{gas_cost_eth:.8f}",
        "don_fee_link": f"{don_fee_link:.6f}",
        "don_fee_juels": str(don_fee_juels),
        "total_estimated": f"{gas_cost_eth:.8f} ETH + {don_fee_link:.6f} LINK",
        "functions_router": FUNCTIONS_ROUTER,
    }


@mcp.tool()
async def chainlink_get_subscription(
    subscription_id: int,
    rpc_url: str | None = None,
) -> dict:
    """Get Chainlink Functions subscription info.

    Args:
        subscription_id: Functions subscription ID
        rpc_url: Optional RPC URL
    """
    rpc = rpc_url or ETHEREUM_RPC_URL
    params = encode(["uint64"], [subscription_id])
    # getSubscription(uint64) selector: 0xa47c7696
    calldata = "0xa47c7696" + params.hex()

    try:
        result_hex = await _eth_call(rpc, FUNCTIONS_ROUTER, calldata)
        data = bytes.fromhex(result_hex.replace("0x", ""))
        balance = int.from_bytes(data[0:32], "big")
        owner = "0x" + data[32:64][-20:].hex()

        return {
            "subscription_id": subscription_id,
            "balance_link": f"{balance / 1e18:.6f}",
            "owner": owner,
            "router": FUNCTIONS_ROUTER,
        }
    except ValueError as e:
        return {"subscription_id": subscription_id, "error": str(e)}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    mcp.run(transport="streamable-http", host="0.0.0.0", port=3007)


if __name__ == "__main__":
    main()
