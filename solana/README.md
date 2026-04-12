# Solana MCP Server

[![License](https://img.shields.io/badge/license-Apache--2.0-green)](../LICENSE)
[![MCP](https://img.shields.io/badge/MCP-2024--11--05-blue)](https://modelcontextprotocol.io)

Solana blockchain MCP server — Jupiter swaps, SPL tokens, Metaplex NFTs, staking, and SNS resolution.

**Live:** `https://solana-mcp.tenzro.network/mcp`

## Tools (14)

| Tool | Description |
|------|-------------|
| `solana_swap` | Jupiter DEX aggregator swap quote |
| `solana_get_price` | Token price via Jupiter Price API v3 |
| `solana_stake` | Staking instructions for validators |
| `solana_get_yield` | APY data for staking protocols |
| `solana_get_balance` | SOL balance for an address |
| `solana_get_token_accounts` | SPL token accounts for an owner |
| `solana_transfer` | Transfer instructions (SOL/SPL) |
| `solana_get_token_info` | Token metadata by mint address |
| `solana_get_nft` | NFT metadata via Metaplex DAS |
| `solana_get_nfts_by_owner` | NFTs owned by an address |
| `solana_get_slot` | Current slot height |
| `solana_get_tps` | Current transactions per second |
| `solana_get_transaction` | Transaction details by signature |
| `solana_resolve_domain` | Bonfida SNS domain resolution |

## Quick Start

```bash
pip install -e .
python server.py --transport http --port 3003
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SOLANA_RPC_URL` | `https://lb.drpc.org/ogrpc?network=solana&dkey=demo` | Solana JSON-RPC |

## Contact

- [tenzro.com](https://tenzro.com) | [eng@tenzro.com](mailto:eng@tenzro.com) | [github.com/tenzro](https://github.com/tenzro)
