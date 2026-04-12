# Tenzro LI.FI MCP Server

Model Context Protocol server for LI.FI cross-chain DEX aggregation — quotes, routing, token discovery, and transaction status tracking via the li.quest REST API.

## Live Endpoint

```
https://lifi-mcp.tenzro.network/mcp
```

## Tools (9)

| Tool | Description |
|------|-------------|
| `lifi_get_chains` | List all supported chains |
| `lifi_get_tokens` | List tokens for one or more chains |
| `lifi_get_token` | Get token details by chain and address/symbol |
| `lifi_get_tools` | List available bridges and DEX aggregators |
| `lifi_get_connections` | Get available connections between two chains |
| `lifi_get_quote` | Get a cross-chain swap quote with calldata |
| `lifi_get_routes` | Get advanced multi-step routes for a swap |
| `lifi_get_status` | Track transaction status by hash |
| `lifi_get_gas_prices` | Get current gas prices for supported chains |

## Quick Start

```bash
# Install
pip install tenzro-lifi-mcp

# Or install from source
pip install -e .

# Run
tenzro-lifi-mcp
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `LIFI_API_URL` | `https://li.quest/v1` | LI.FI API base URL |
| `LIFI_API_KEY` | (none) | Optional LI.FI API key for higher rate limits |
| `MCP_HOST` | `0.0.0.0` | Server bind host |
| `MCP_PORT` | `3008` | Server bind port |

## Notes

- LI.FI aggregates 30+ bridges and DEXes across 35+ chains
- Quotes include ready-to-sign calldata for direct execution
- The advanced routes endpoint supports multi-hop and split routes
- No API key required for basic usage; key recommended for production

## License

Apache-2.0
