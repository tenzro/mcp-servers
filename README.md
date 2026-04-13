# Tenzro MCP Servers

[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-2024--11--05-blue)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://python.org)

Open-source [Model Context Protocol](https://modelcontextprotocol.io) servers for blockchain and cross-chain operations. Built by [Tenzro](https://tenzro.com).

## Servers

| Server | Tools | Description | Live Endpoint |
|--------|-------|-------------|--------------|
| [Tenzro](tenzro/) | 146 | Tenzro L1 — wallets, identity, tokens, NFTs, agents, crypto, TEE, ZK, custody | `mcp.tenzro.network/mcp` |
| [Solana](solana/) | 14 | Jupiter swaps, SPL tokens, Metaplex NFTs, staking, SNS | `solana-mcp.tenzro.network/mcp` |
| [Ethereum](ethereum/) | 16 | Gas, ENS, ERC-20, EAS attestations, ERC-8004 agents | `ethereum-mcp.tenzro.network/mcp` |
| [Canton](canton/) | 14 | DAML contracts, CIP-56 tokens, DvP settlement | `canton-mcp.tenzro.network/mcp` |
| [LayerZero](layerzero/) | 20 | V2 messaging, OFT transfers, Stargate bridging | `layerzero-mcp.tenzro.network/mcp` |
| [Chainlink](chainlink/) | 20 | CCIP, data feeds, VRF, automation, Functions | `chainlink-mcp.tenzro.network/mcp` |
| [LI.FI](lifi/) | 9 | Cross-chain aggregator — 66 chains, quotes, routes, swaps | `lifi-mcp.tenzro.network/mcp` |

**Total: 239 tools across 7 servers**

Also integrates with official hosted MCPs:
- [deBridge](https://agents.debridge.com/mcp) — 5 tools (cross-chain DLN swaps)
- [1inch](https://api.1inch.com/mcp/protocol) — 7 tools (DEX aggregation, Fusion swaps)

## Quick Start

Each server runs standalone:

```bash
cd lifi
pip install -e .
python server.py                               # stdio (Claude Desktop)
python server.py --transport http --port 3008   # Streamable HTTP
```

Or connect to the live Tenzro testnet endpoints directly — no installation needed.

### Claude Desktop

```json
{
  "mcpServers": {
    "tenzro": { "command": "npx", "args": ["-y", "mcp-remote", "https://mcp.tenzro.network/mcp"] },
    "tenzro-solana": { "command": "npx", "args": ["-y", "mcp-remote", "https://solana-mcp.tenzro.network/mcp"] },
    "tenzro-ethereum": { "command": "npx", "args": ["-y", "mcp-remote", "https://ethereum-mcp.tenzro.network/mcp"] },
    "tenzro-lifi": { "command": "npx", "args": ["-y", "mcp-remote", "https://lifi-mcp.tenzro.network/mcp"] },
    "tenzro-layerzero": { "command": "npx", "args": ["-y", "mcp-remote", "https://layerzero-mcp.tenzro.network/mcp"] },
    "tenzro-chainlink": { "command": "npx", "args": ["-y", "mcp-remote", "https://chainlink-mcp.tenzro.network/mcp"] }
  }
}
```

### Claude Code

```bash
claude mcp add --transport http tenzro-lifi https://lifi-mcp.tenzro.network/mcp
claude mcp add --transport http tenzro-solana https://solana-mcp.tenzro.network/mcp
```

## Architecture

All servers are lightweight Python proxies using [FastMCP](https://gofastmcp.com) 3.x. They call external APIs and expose results as MCP tools.

```
Agent (Claude, Cursor, GPT, etc.)
    |
    ├── Tenzro MCP ──→ rpc.tenzro.network (Tenzro L1)
    ├── Solana MCP ──→ Solana RPC via dRPC
    ├── Ethereum MCP ──→ Ethereum RPC via dRPC
    ├── Canton MCP ──→ Canton JSON Ledger API v2
    ├── LayerZero MCP ──→ LayerZero contracts via dRPC
    ├── Chainlink MCP ──→ Chainlink contracts via dRPC
    └── LI.FI MCP ──→ li.quest REST API (66 chains)
```

## Contributing

Each server is self-contained in its own directory. To add a tool:

1. Add the function with `@mcp.tool` decorator in `server.py`
2. Update the README tool table
3. Test against the live API
4. Submit a PR

## Contact

- Website: [tenzro.com](https://tenzro.com)
- Engineering: [eng@tenzro.com](mailto:eng@tenzro.com)
- GitHub: [github.com/tenzro](https://github.com/tenzro)

## License

Apache 2.0. See [LICENSE](LICENSE).
