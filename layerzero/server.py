"""Tenzro LayerZero MCP Server — 20 tools for LayerZero V2 cross-chain messaging."""

import json
import os
import struct
from typing import Any

import httpx
from eth_abi import encode
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tenzro-layerzero-mcp")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ETHEREUM_RPC_URL = os.environ.get("ETHEREUM_RPC_URL", "https://eth.llamarpc.com")
LZ_SCAN_API = os.environ.get("LAYERZERO_SCAN_API_URL", "https://scan.layerzero-api.com")
LZ_METADATA_API = os.environ.get("LAYERZERO_METADATA_API_URL", "https://metadata.layerzero-api.com")

ENDPOINT_V2 = "0x1a44076050125825900e736c501f859c50fE728c"
STARGATE_POOL_NATIVE_ETH = "0x77b2043768d28E9C9aB44E1aBfC95944bcE57931"

# quote() selector on EndpointV2
QUOTE_SELECTOR = "0xdb9d28c6"
# send() selector on EndpointV2
SEND_SELECTOR = "0x5e280f11"

# Supported chains with their endpoint IDs and default RPCs
CHAINS: dict[str, dict[str, Any]] = {
    "ethereum":  {"eid": 30101, "chain_id": 1,     "rpc": "https://eth.llamarpc.com"},
    "bsc":       {"eid": 30102, "chain_id": 56,    "rpc": "https://bsc-dataseed.binance.org"},
    "avalanche": {"eid": 30106, "chain_id": 43114, "rpc": "https://api.avax.network/ext/bc/C/rpc"},
    "polygon":   {"eid": 30109, "chain_id": 137,   "rpc": "https://polygon-rpc.com"},
    "arbitrum":  {"eid": 30110, "chain_id": 42161, "rpc": "https://arb1.arbitrum.io/rpc"},
    "optimism":  {"eid": 30111, "chain_id": 10,    "rpc": "https://mainnet.optimism.io"},
    "zkSync":    {"eid": 30165, "chain_id": 324,   "rpc": "https://mainnet.era.zksync.io"},
    "solana":    {"eid": 30168, "chain_id": 0,     "rpc": "https://api.mainnet-beta.solana.com"},
    "base":      {"eid": 30184, "chain_id": 8453,  "rpc": "https://mainnet.base.org"},
    "sei":       {"eid": 30280, "chain_id": 1329,  "rpc": "https://evm-rpc.sei-apis.com"},
    "sonic":     {"eid": 30332, "chain_id": 146,   "rpc": "https://rpc.soniclabs.com"},
    "berachain": {"eid": 30362, "chain_id": 80094, "rpc": "https://rpc.berachain.com"},
    "story":     {"eid": 30364, "chain_id": 1514,  "rpc": "https://mainnet.storyrpc.io"},
    "monad":     {"eid": 30390, "chain_id": 143,   "rpc": "https://rpc.monad.xyz"},
    "megaeth":   {"eid": 30398, "chain_id": 6342,  "rpc": "https://rpc.megaeth.com"},
    "tron":      {"eid": 30420, "chain_id": 728126428, "rpc": "https://api.trongrid.io/jsonrpc"},
}

# Well-known DVNs
DVNS = [
    {"name": "LayerZero Labs", "address": "0x589dEDbD617eE1530a6a00E8aEbB1bBe650bB8dE"},
    {"name": "Google Cloud", "address": "0xD56e4eAb23cb81f43168F9F45211Eb027b9aC7cc"},
    {"name": "Polyhedra", "address": "0x8ddf05F9A5c488b4973897E278B58895bF87Cb24"},
    {"name": "Animoca Blockdaemon", "address": "0xc097ab8CD7b053326DFe9fB3E3a31a0CCe3B526f"},
    {"name": "Nethermind", "address": "0xa59BA433ac34D2927232ECb54B3f614cCE1e3371"},
    {"name": "Stargate", "address": "0xAD0c8239C969E46B13db33e6C6Bfd29592B56f14"},
]

# Stargate V2 pool addresses (Ethereum mainnet)
STARGATE_POOLS = {
    "ETH": {"address": STARGATE_POOL_NATIVE_ETH, "type": "native"},
    "USDC": {"address": "0xc026395860Db2d07ee33e05fE50ed7bD583189C7", "type": "erc20"},
    "USDT": {"address": "0x933597a323Eb81cAe705C5bC29985172fd5A3973", "type": "erc20"},
}

_http = httpx.AsyncClient(timeout=30)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _eth_call(rpc_url: str, to: str, data: str) -> str:
    """Execute an eth_call and return the hex result."""
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


def _get_rpc(chain: str) -> str:
    """Resolve RPC URL for a chain name."""
    if chain.lower() == "ethereum":
        return os.environ.get("ETHEREUM_RPC_URL", CHAINS["ethereum"]["rpc"])
    info = CHAINS.get(chain.lower())
    if not info:
        raise ValueError(f"Unknown chain: {chain}. Supported: {', '.join(CHAINS.keys())}")
    return info["rpc"]


def _get_eid(chain: str) -> int:
    info = CHAINS.get(chain.lower())
    if not info:
        raise ValueError(f"Unknown chain: {chain}")
    return info["eid"]


def _pad32(b: bytes) -> bytes:
    return b.rjust(32, b"\x00")


def _address_to_bytes32(addr: str) -> bytes:
    addr_bytes = bytes.fromhex(addr.replace("0x", ""))
    return _pad32(addr_bytes)


def _encode_options(gas_limit: int, value: int = 0) -> bytes:
    """Encode TYPE_3 executor options for lzReceive."""
    # TYPE_3 tag
    tag = b"\x00\x03"
    # Worker ID 1 (executor), option type 1 (lzReceive)
    worker_id = (1).to_bytes(1, "big")
    if value > 0:
        option_type = (3).to_bytes(1, "big")  # lzReceive with value
        option_data = gas_limit.to_bytes(16, "big") + value.to_bytes(16, "big")
        option_length = (1 + len(option_data)).to_bytes(2, "big")
    else:
        option_type = (1).to_bytes(1, "big")  # lzReceive gas only
        option_data = gas_limit.to_bytes(16, "big")
        option_length = (1 + len(option_data)).to_bytes(2, "big")
    return tag + option_length + worker_id + option_type + option_data


# ---------------------------------------------------------------------------
# Tools — Messaging
# ---------------------------------------------------------------------------

@mcp.tool()
async def lz_quote_fee(
    src_chain: str,
    dst_chain: str,
    receiver: str,
    message: str = "0x",
    gas_limit: int = 200_000,
    value: int = 0,
) -> dict:
    """Quote the messaging fee for a cross-chain message via EndpointV2.quote().

    Args:
        src_chain: Source chain name (e.g. "ethereum", "arbitrum")
        dst_chain: Destination chain name
        receiver: Destination receiver address (0x...)
        message: Hex-encoded message payload (default empty)
        gas_limit: Gas limit for lzReceive on destination
        value: Native value to send with lzReceive (wei)
    """
    rpc = _get_rpc(src_chain)
    dst_eid = _get_eid(dst_chain)
    options = _encode_options(gas_limit, value)
    msg_bytes = bytes.fromhex(message.replace("0x", "")) if message != "0x" else b""

    # MessagingParams: (uint32 dstEid, bytes32 receiver, bytes message, bytes options, bool payInLzToken)
    params_encoded = encode(
        ["(uint32,bytes32,bytes,bytes,bool)"],
        [(dst_eid, _address_to_bytes32(receiver), msg_bytes, options, False)],
    )
    calldata = QUOTE_SELECTOR + params_encoded.hex()

    result_hex = await _eth_call(rpc, ENDPOINT_V2, calldata)
    # Returns (uint256 nativeFee, uint256 lzTokenFee)
    data = bytes.fromhex(result_hex.replace("0x", ""))
    native_fee = int.from_bytes(data[0:32], "big")
    lz_token_fee = int.from_bytes(data[32:64], "big")

    return {
        "native_fee_wei": str(native_fee),
        "native_fee_eth": f"{native_fee / 1e18:.8f}",
        "lz_token_fee_wei": str(lz_token_fee),
        "src_chain": src_chain,
        "dst_chain": dst_chain,
        "dst_eid": dst_eid,
        "gas_limit": gas_limit,
    }


@mcp.tool()
async def lz_send_message(
    src_chain: str,
    dst_chain: str,
    sender: str,
    receiver: str,
    message: str = "0x",
    gas_limit: int = 200_000,
    value: int = 0,
    native_fee_wei: str | None = None,
) -> dict:
    """Build EndpointV2.send() calldata for a cross-chain message.

    Returns the calldata and value to submit as a transaction. Does NOT broadcast.

    Args:
        src_chain: Source chain name
        dst_chain: Destination chain name
        sender: Sender address on source chain
        receiver: Receiver address on destination chain
        message: Hex-encoded message payload
        gas_limit: Destination gas limit
        value: Native value for lzReceive (wei)
        native_fee_wei: Fee in wei (if None, quotes automatically)
    """
    dst_eid = _get_eid(dst_chain)
    options = _encode_options(gas_limit, value)
    msg_bytes = bytes.fromhex(message.replace("0x", "")) if message != "0x" else b""

    if native_fee_wei is None:
        quote = await lz_quote_fee(src_chain, dst_chain, receiver, message, gas_limit, value)
        fee = int(quote["native_fee_wei"])
    else:
        fee = int(native_fee_wei)

    # send(MessagingParams, address refundAddress)
    # MessagingParams = (uint32, bytes32, bytes, bytes, bool)
    # MessagingFee = (uint256 nativeFee, uint256 lzTokenFee)
    params_encoded = encode(
        ["(uint32,bytes32,bytes,bytes,bool)", "(uint256,uint256)", "address"],
        [
            (dst_eid, _address_to_bytes32(receiver), msg_bytes, options, False),
            (fee, 0),
            sender,
        ],
    )
    calldata = SEND_SELECTOR + params_encoded.hex()

    return {
        "to": ENDPOINT_V2,
        "calldata": "0x" + calldata,
        "value_wei": str(fee),
        "src_chain": src_chain,
        "dst_chain": dst_chain,
        "dst_eid": dst_eid,
        "description": f"LayerZero V2 send() from {src_chain} to {dst_chain}",
    }


@mcp.tool()
async def lz_track_message(tx_hash: str) -> dict:
    """Track a LayerZero message by source transaction hash via the Scan API.

    Args:
        tx_hash: Source chain transaction hash
    """
    url = f"{LZ_SCAN_API}/v1/messages/tx/{tx_hash}"
    resp = await _http.get(url)
    if resp.status_code == 404:
        return {"status": "NOT_FOUND", "tx_hash": tx_hash}
    resp.raise_for_status()
    data = resp.json()
    messages = data.get("messages", data.get("data", []))
    if not messages:
        return {"status": "NOT_FOUND", "tx_hash": tx_hash}

    msg = messages[0] if isinstance(messages, list) else messages
    return {
        "status": msg.get("status", "UNKNOWN"),
        "src_chain_id": msg.get("srcChainId"),
        "dst_chain_id": msg.get("dstChainId"),
        "src_tx_hash": msg.get("srcTxHash", tx_hash),
        "dst_tx_hash": msg.get("dstTxHash"),
        "guid": msg.get("guid"),
        "nonce": msg.get("nonce"),
        "created": msg.get("created"),
        "updated": msg.get("updated"),
    }


@mcp.tool()
async def lz_get_message(guid: str) -> dict:
    """Get a LayerZero message by its GUID.

    Args:
        guid: Message GUID (globally unique identifier)
    """
    url = f"{LZ_SCAN_API}/v1/messages/{guid}"
    resp = await _http.get(url)
    if resp.status_code == 404:
        return {"status": "NOT_FOUND", "guid": guid}
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Tools — OFT
# ---------------------------------------------------------------------------

@mcp.tool()
async def lz_oft_quote(
    oft_address: str,
    src_chain: str,
    dst_chain: str,
    amount: str,
    receiver: str,
    gas_limit: int = 200_000,
) -> dict:
    """Quote an OFT cross-chain token transfer.

    Args:
        oft_address: OFT contract address on source chain
        src_chain: Source chain name
        dst_chain: Destination chain name
        amount: Token amount in smallest unit (e.g. wei)
        receiver: Destination receiver address
        gas_limit: Gas limit for lzReceive
    """
    rpc = _get_rpc(src_chain)
    dst_eid = _get_eid(dst_chain)
    options = _encode_options(gas_limit)

    # OFT.quoteSend((uint32 dstEid, bytes32 to, uint256 amountLD, uint256 minAmountLD, bytes extraOptions, bytes composeMsg, bytes oftCmd), bool payInLzToken)
    send_param = encode(
        ["(uint32,bytes32,uint256,uint256,bytes,bytes,bytes)", "bool"],
        [
            (dst_eid, _address_to_bytes32(receiver), int(amount), 0, options, b"", b""),
            False,
        ],
    )
    # quoteSend selector
    calldata = "0xc7c7f5b3" + send_param.hex()

    result_hex = await _eth_call(rpc, oft_address, calldata)
    data = bytes.fromhex(result_hex.replace("0x", ""))
    # Returns (MessagingFee(uint256 nativeFee, uint256 lzTokenFee), OFTReceipt(uint256 amountSentLD, uint256 amountReceivedLD))
    native_fee = int.from_bytes(data[0:32], "big")
    lz_token_fee = int.from_bytes(data[32:64], "big")
    amount_sent = int.from_bytes(data[64:96], "big")
    amount_received = int.from_bytes(data[96:128], "big")

    return {
        "native_fee_wei": str(native_fee),
        "native_fee_eth": f"{native_fee / 1e18:.8f}",
        "lz_token_fee_wei": str(lz_token_fee),
        "amount_sent": str(amount_sent),
        "amount_received": str(amount_received),
        "oft_address": oft_address,
        "dst_eid": dst_eid,
    }


@mcp.tool()
async def lz_oft_send(
    oft_address: str,
    src_chain: str,
    dst_chain: str,
    sender: str,
    receiver: str,
    amount: str,
    gas_limit: int = 200_000,
) -> dict:
    """Build OFT send() calldata for a cross-chain token transfer.

    Returns calldata and value. Does NOT broadcast.

    Args:
        oft_address: OFT contract address on source chain
        src_chain: Source chain name
        dst_chain: Destination chain name
        sender: Sender address
        receiver: Destination receiver address
        amount: Token amount in smallest unit
        gas_limit: Destination gas limit
    """
    # First get the quote for fee
    quote = await lz_oft_quote(oft_address, src_chain, dst_chain, amount, receiver, gas_limit)
    fee = int(quote["native_fee_wei"])
    dst_eid = _get_eid(dst_chain)
    options = _encode_options(gas_limit)

    # OFT.send((uint32,bytes32,uint256,uint256,bytes,bytes,bytes), (uint256,uint256), address)
    send_param = encode(
        ["(uint32,bytes32,uint256,uint256,bytes,bytes,bytes)", "(uint256,uint256)", "address"],
        [
            (dst_eid, _address_to_bytes32(receiver), int(amount), 0, options, b"", b""),
            (fee, 0),
            sender,
        ],
    )
    # send() selector
    calldata = "0xc7c7f5b3" + send_param.hex()

    return {
        "to": oft_address,
        "calldata": "0x" + calldata,
        "value_wei": str(fee),
        "native_fee_eth": quote["native_fee_eth"],
        "amount_sent": quote["amount_sent"],
        "amount_received": quote["amount_received"],
        "description": f"OFT send {amount} from {src_chain} to {dst_chain}",
    }


# ---------------------------------------------------------------------------
# Tools — Network info
# ---------------------------------------------------------------------------

@mcp.tool()
async def lz_list_chains() -> dict:
    """List all 16 supported chains with their LayerZero endpoint IDs and chain IDs."""
    chains = []
    for name, info in CHAINS.items():
        chains.append({
            "name": name,
            "eid": info["eid"],
            "chain_id": info["chain_id"],
        })
    return {"chains": chains, "count": len(chains)}


@mcp.tool()
async def lz_get_chain_rpc(chain: str) -> dict:
    """Get the default RPC URL for a chain.

    Args:
        chain: Chain name (e.g. "ethereum", "arbitrum", "base")
    """
    rpc = _get_rpc(chain)
    info = CHAINS[chain.lower()]
    return {
        "chain": chain,
        "rpc_url": rpc,
        "eid": info["eid"],
        "chain_id": info["chain_id"],
    }


@mcp.tool()
async def lz_list_dvns() -> dict:
    """List known Decentralized Verifier Networks (DVNs) on LayerZero V2."""
    return {"dvns": DVNS, "count": len(DVNS)}


@mcp.tool()
async def lz_get_deployments() -> dict:
    """Get LayerZero V2 deployment addresses."""
    return {
        "endpoint_v2": ENDPOINT_V2,
        "stargate_pools": STARGATE_POOLS,
        "note": "EndpointV2 address is the same on all EVM chains",
    }


@mcp.tool()
async def lz_get_messages_by_address(address: str, limit: int = 10) -> dict:
    """Get LayerZero messages sent or received by an address.

    Args:
        address: Wallet address to search
        limit: Maximum number of messages to return (default 10)
    """
    url = f"{LZ_SCAN_API}/v1/messages/address/{address}"
    resp = await _http.get(url, params={"limit": limit})
    if resp.status_code == 404:
        return {"messages": [], "address": address}
    resp.raise_for_status()
    data = resp.json()
    messages = data.get("messages", data.get("data", []))
    return {"messages": messages[:limit], "address": address, "count": len(messages)}


# ---------------------------------------------------------------------------
# Tools — Value Transfer API
# ---------------------------------------------------------------------------

@mcp.tool()
async def lz_transfer_quote(
    src_chain: str,
    dst_chain: str,
    token: str,
    amount: str,
    sender: str,
    receiver: str | None = None,
) -> dict:
    """Quote a cross-chain token transfer via the LayerZero Value Transfer API (130+ chains).

    Args:
        src_chain: Source chain name or chain ID
        dst_chain: Destination chain name or chain ID
        token: Token symbol or address
        amount: Amount in smallest unit
        sender: Sender address
        receiver: Receiver address (defaults to sender)
    """
    url = f"{LZ_METADATA_API}/v1/transfer/quote"
    params = {
        "srcChain": src_chain,
        "dstChain": dst_chain,
        "token": token,
        "amount": amount,
        "sender": sender,
        "receiver": receiver or sender,
    }
    resp = await _http.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
async def lz_transfer_build(quote_id: str) -> dict:
    """Build signable transaction steps from a Value Transfer API quote.

    Args:
        quote_id: Quote ID returned from lz_transfer_quote
    """
    url = f"{LZ_METADATA_API}/v1/transfer/build"
    resp = await _http.get(url, params={"quoteId": quote_id})
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
async def lz_transfer_status(quote_id: str) -> dict:
    """Track the status of a Value Transfer API transfer.

    Args:
        quote_id: Quote ID to track
    """
    url = f"{LZ_METADATA_API}/v1/transfer/status"
    resp = await _http.get(url, params={"quoteId": quote_id})
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
async def lz_transfer_chains() -> dict:
    """List all chains supported by the LayerZero Value Transfer API (130+ chains)."""
    url = f"{LZ_METADATA_API}/v1/transfer/chains"
    resp = await _http.get(url)
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
async def lz_transfer_tokens(chain: str | None = None) -> dict:
    """List available tokens for the Value Transfer API, optionally filtered by chain.

    Args:
        chain: Optional chain name or ID to filter tokens
    """
    url = f"{LZ_METADATA_API}/v1/transfer/tokens"
    params = {}
    if chain:
        params["chain"] = chain
    resp = await _http.get(url, params=params)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Tools — Stargate V2
# ---------------------------------------------------------------------------

@mcp.tool()
async def lz_stargate_quote(
    src_chain: str,
    dst_chain: str,
    token: str,
    amount: str,
    receiver: str,
    gas_limit: int = 200_000,
) -> dict:
    """Quote a Stargate V2 native bridging fee via quoteSend().

    Args:
        src_chain: Source chain name
        dst_chain: Destination chain name
        token: Token symbol (ETH, USDC, USDT)
        amount: Amount in smallest unit (wei for ETH)
        receiver: Destination receiver address
        gas_limit: Destination gas limit
    """
    pool = STARGATE_POOLS.get(token.upper())
    if not pool:
        return {"error": f"Unknown Stargate token: {token}. Supported: {', '.join(STARGATE_POOLS.keys())}"}

    rpc = _get_rpc(src_chain)
    dst_eid = _get_eid(dst_chain)
    options = _encode_options(gas_limit)

    # quoteSend((uint32 dstEid, bytes32 to, uint256 amountLD, uint256 minAmountLD, bytes extraOptions, bytes composeMsg, bytes oftCmd), bool payInLzToken)
    params_encoded = encode(
        ["(uint32,bytes32,uint256,uint256,bytes,bytes,bytes)", "bool"],
        [
            (dst_eid, _address_to_bytes32(receiver), int(amount), 0, options, b"", b""),
            False,
        ],
    )
    calldata = "0xc7c7f5b3" + params_encoded.hex()

    result_hex = await _eth_call(rpc, pool["address"], calldata)
    data = bytes.fromhex(result_hex.replace("0x", ""))
    native_fee = int.from_bytes(data[0:32], "big")

    return {
        "native_fee_wei": str(native_fee),
        "native_fee_eth": f"{native_fee / 1e18:.8f}",
        "pool_address": pool["address"],
        "pool_type": pool["type"],
        "token": token.upper(),
        "dst_eid": dst_eid,
    }


@mcp.tool()
async def lz_stargate_send(
    src_chain: str,
    dst_chain: str,
    token: str,
    amount: str,
    sender: str,
    receiver: str,
    gas_limit: int = 200_000,
) -> dict:
    """Build Stargate V2 sendToken() calldata for native bridging.

    Returns calldata and value. For ERC-20 tokens, also includes an approval step.

    Args:
        src_chain: Source chain name
        dst_chain: Destination chain name
        token: Token symbol (ETH, USDC, USDT)
        amount: Amount in smallest unit
        sender: Sender address
        receiver: Destination receiver address
        gas_limit: Destination gas limit
    """
    pool = STARGATE_POOLS.get(token.upper())
    if not pool:
        return {"error": f"Unknown Stargate token: {token}. Supported: {', '.join(STARGATE_POOLS.keys())}"}

    quote = await lz_stargate_quote(src_chain, dst_chain, token, amount, receiver, gas_limit)
    if "error" in quote:
        return quote

    fee = int(quote["native_fee_wei"])
    dst_eid = _get_eid(dst_chain)
    options = _encode_options(gas_limit)

    # sendToken((uint32,bytes32,uint256,uint256,bytes,bytes,bytes), (uint256,uint256), address)
    params_encoded = encode(
        ["(uint32,bytes32,uint256,uint256,bytes,bytes,bytes)", "(uint256,uint256)", "address"],
        [
            (dst_eid, _address_to_bytes32(receiver), int(amount), 0, options, b"", b""),
            (fee, 0),
            sender,
        ],
    )
    # sendToken selector
    calldata = "0x5e280f11" + params_encoded.hex()

    tx_value = fee + int(amount) if pool["type"] == "native" else fee

    steps = []
    if pool["type"] == "erc20":
        # ERC-20 approval step
        approve_data = encode(["address", "uint256"], [pool["address"], int(amount)])
        steps.append({
            "step": "approve",
            "to": "TOKEN_ADDRESS",
            "calldata": "0x095ea7b3" + approve_data.hex(),
            "value_wei": "0",
            "description": f"Approve {token} spend by Stargate pool",
        })

    steps.append({
        "step": "send",
        "to": pool["address"],
        "calldata": "0x" + calldata,
        "value_wei": str(tx_value),
        "description": f"Stargate sendToken {amount} {token} from {src_chain} to {dst_chain}",
    })

    return {
        "steps": steps,
        "native_fee_eth": quote["native_fee_eth"],
        "pool_address": pool["address"],
    }


# ---------------------------------------------------------------------------
# Tools — Options encoding
# ---------------------------------------------------------------------------

@mcp.tool()
async def lz_encode_options(gas_limit: int, value: int = 0) -> dict:
    """Encode TYPE_3 executor options for lzReceive.

    Args:
        gas_limit: Gas limit for destination execution (uint128)
        value: Native value to forward on destination (uint128, default 0)
    """
    opts = _encode_options(gas_limit, value)
    return {
        "options_hex": "0x" + opts.hex(),
        "options_length": len(opts),
        "gas_limit": gas_limit,
        "value": value,
        "type": 3,
        "description": "TYPE_3 lzReceive option" + (f" with {value} wei value" if value else ""),
    }


@mcp.tool()
async def lz_get_token_pool(token: str) -> dict:
    """Get Stargate V2 pool info for a token.

    Args:
        token: Token symbol (ETH, USDC, USDT)
    """
    pool = STARGATE_POOLS.get(token.upper())
    if not pool:
        return {
            "error": f"Unknown token: {token}",
            "supported_tokens": list(STARGATE_POOLS.keys()),
        }
    return {
        "token": token.upper(),
        "pool_address": pool["address"],
        "pool_type": pool["type"],
        "protocol": "Stargate V2",
        "chains": list(CHAINS.keys()),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    mcp.run(transport="streamable-http", host="0.0.0.0", port=3006)


if __name__ == "__main__":
    main()
