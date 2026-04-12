# Tenzro LayerZero MCP Server

Model Context Protocol server for LayerZero V2 cross-chain messaging, OFT transfers, Stargate bridging, and the Value Transfer API.

## Live Endpoint

```
https://layerzero-mcp.tenzro.network/mcp
```

## Tools (20)

| Tool | Description |
|------|-------------|
| `lz_quote_fee` | Quote messaging fee via EndpointV2.quote() eth_call |
| `lz_send_message` | Build EndpointV2.send() calldata for cross-chain message |
| `lz_track_message` | Track message delivery status via LayerZero Scan API |
| `lz_get_message` | Get message details by GUID |
| `lz_oft_quote` | Quote OFT cross-chain token transfer via Metadata API |
| `lz_oft_send` | Build OFT send() calldata with uint64 amountSD |
| `lz_list_chains` | List 16 supported chains with endpoint IDs |
| `lz_get_chain_rpc` | Get default RPC URL for a chain |
| `lz_list_dvns` | List Decentralized Verifier Networks |
| `lz_get_deployments` | Get LayerZero deployment addresses per chain |
| `lz_transfer_quote` | Quote cross-chain transfer via Value Transfer API (130+ chains) |
| `lz_transfer_build` | Build signable transaction steps from a transfer quote |
| `lz_transfer_status` | Track transfer status by quote ID |
| `lz_transfer_chains` | List all chains supported by the Value Transfer API |
| `lz_transfer_tokens` | List available tokens, optionally filtered by chain |
| `lz_stargate_quote` | Quote Stargate V2 native bridging via quoteSend() |
| `lz_stargate_send` | Build Stargate sendToken() calldata |
| `lz_get_messages_by_address` | Get messages sent or received by an address |
| `lz_encode_options` | Encode TYPE_3 executor options (lzReceive gas + value) |
| `lz_get_token_pool` | Get Stargate pool info for a token |

## Quick Start

```bash
# Install
pip install tenzro-layerzero-mcp

# Or install from source
pip install -e .

# Run
tenzro-layerzero-mcp
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `ETHEREUM_RPC_URL` | `https://eth.llamarpc.com` | Default Ethereum RPC endpoint |
| `LAYERZERO_SCAN_API_URL` | `https://scan.layerzero-api.com` | LayerZero Scan API base URL |
| `LAYERZERO_METADATA_API_URL` | `https://metadata.layerzero-api.com` | LayerZero Metadata API base URL |
| `MCP_HOST` | `0.0.0.0` | Server bind host |
| `MCP_PORT` | `3006` | Server bind port |

## Contract Addresses

- **EndpointV2**: `0x1a44076050125825900e736c501f859c50fE728c` (all EVM chains)
- **StargatePoolNative (ETH)**: `0x77b2043768d28E9C9aB44E1aBfC95944bcE57931`

## License

Apache-2.0
