# Tenzro Chainlink MCP Server

Model Context Protocol server for Chainlink CCIP cross-chain messaging, data feeds, Data Streams, VRF v2.5, Proof of Reserve, Automation, and Functions.

## Live Endpoint

```
https://chainlink-mcp.tenzro.network/mcp
```

## Tools (20)

| Tool | Description |
|------|-------------|
| `chainlink_get_price` | Get latest price from AggregatorV3 feed via latestRoundData() |
| `chainlink_list_feeds` | List known Chainlink price feed addresses |
| `ccip_get_fee` | Quote CCIP cross-chain message fee via Router.getFee() |
| `ccip_send_message` | Build Router.ccipSend() calldata for cross-chain message |
| `ccip_track_message` | Track CCIP message execution state via OffRamp |
| `ccip_get_supported_chains` | List CCIP chain selectors |
| `ccip_get_supported_tokens` | List supported tokens per CCIP chain |
| `ccip_get_lanes` | List available CCIP lanes |
| `ccip_get_token_pool` | Get CCT v1.6+ token pool info |
| `ccip_get_rate_limits` | Get per-lane rate limiter configuration |
| `ds_get_report` | Get Data Streams report for sub-second market data |
| `ds_list_feeds` | List available Data Streams feeds |
| `vrf_request_random` | Build VRF v2.5 requestRandomWords() calldata |
| `vrf_get_subscription` | Get VRF subscription info (balance, consumers) |
| `por_get_reserve` | Read Proof of Reserve feed value |
| `por_list_feeds` | List Proof of Reserve feeds |
| `chainlink_check_upkeep` | Dry-run Automation checkUpkeep() |
| `chainlink_get_upkeep_info` | Get Automation upkeep info from registry |
| `chainlink_estimate_functions_cost` | Estimate Chainlink Functions DON execution cost |
| `chainlink_get_subscription` | Get Functions subscription info |

## Quick Start

```bash
# Install
pip install tenzro-chainlink-mcp

# Or install from source
pip install -e .

# Run
tenzro-chainlink-mcp
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `ETHEREUM_RPC_URL` | `https://eth.llamarpc.com` | Default Ethereum RPC endpoint |
| `CHAINLINK_DATA_STREAMS_API` | `https://api.chainlink-data-streams.io` | Data Streams API URL |
| `MCP_HOST` | `0.0.0.0` | Server bind host |
| `MCP_PORT` | `3007` | Server bind port |

## Key Addresses (Ethereum Mainnet)

- **CCIP Router**: `0x80226fc0Ee2b096224EeAc085Bb9a8cba1146f7D`
- **VRF Coordinator v2.5**: `0xD7f86b4b8Cae7D942340FF628F82735b7a20893a`
- **Automation Registry v2.1**: `0x6593c7De001fC8542bB1703532EE1E5aA0D458fD`
- **Functions Router**: `0x65Dcc24F8ff9e51F10DCc7Ed1e4e2A61e6E14bd6`

## License

Apache-2.0
