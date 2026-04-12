# Ethereum MCP Server

[![License](https://img.shields.io/badge/license-Apache--2.0-green)](../LICENSE)
[![MCP](https://img.shields.io/badge/MCP-2024--11--05-blue)](https://modelcontextprotocol.io)

Ethereum blockchain MCP server — Chainlink price feeds, ENS, ERC-20 tokens, ERC-8004 agents, EAS attestations, and core RPC.

**Live:** `https://ethereum-mcp.tenzro.network/mcp`

## Tools (16)

| Tool | Description |
|------|-------------|
| `eth_get_price` | Token price via Chainlink AggregatorV3 |
| `eth_get_gas_price` | Current gas price |
| `eth_estimate_gas` | Estimate gas for a transaction |
| `eth_get_fee_history` | Fee history for recent blocks |
| `eth_get_balance` | ETH balance for an address |
| `eth_get_token_balance` | ERC-20 token balance |
| `eth_get_transaction` | Transaction details by hash |
| `eth_get_block` | Block details by number |
| `eth_get_transaction_receipt` | Transaction receipt by hash |
| `eth_resolve_ens` | Resolve ENS name to address |
| `eth_lookup_ens` | Reverse ENS lookup (address to name) |
| `eth_call_contract` | Read-only contract call |
| `eth_encode_function` | ABI encode a function call |
| `eth_register_agent_8004` | Build ERC-8004 registerAgent calldata |
| `eth_lookup_agent_8004` | Build ERC-8004 getAgent calldata |
| `eth_get_attestation` | Query EAS attestation by UID |

## Quick Start

```bash
pip install -e .
python server.py --transport http --port 3004
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ETHEREUM_RPC_URL` | dRPC endpoint | Ethereum JSON-RPC |

## Contact

- [tenzro.com](https://tenzro.com) | [eng@tenzro.com](mailto:eng@tenzro.com) | [github.com/tenzro](https://github.com/tenzro)
