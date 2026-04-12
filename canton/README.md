# Tenzro Canton MCP Server

Model Context Protocol server for Canton 3.x / DAML, using the JSON Ledger API v2 for contract management, party administration, DvP settlement, and CIP-56 tokenization.

## Live Endpoint

```
https://canton-mcp.tenzro.network/mcp
```

## Tools (14)

| Tool | Description |
|------|-------------|
| `canton_submit_command` | Submit a DAML command and wait for transaction result |
| `canton_list_contracts` | List active contracts filtered by template and party |
| `canton_get_events` | Get create/archive events for a contract ID |
| `canton_get_transaction` | Get transaction details by transaction ID |
| `canton_allocate_party` | Allocate a new party on the ledger |
| `canton_list_parties` | List all known parties |
| `canton_list_domains` | List synchronizer domains (Admin API) |
| `canton_get_health` | Check Canton node health status |
| `canton_get_balance` | Query CIP-56 token holding balance |
| `canton_transfer` | Execute a CIP-56 token transfer |
| `canton_create_asset` | Create a new DAML contract (asset) |
| `canton_dvp_settle` | Execute a Delivery vs Payment settlement |
| `canton_upload_dar` | Upload a DAR package to the ledger |
| `canton_get_fee_schedule` | Get synchronizer fee schedule (Admin API) |

## Quick Start

```bash
# Install
pip install tenzro-canton-mcp

# Or install from source
pip install -e .

# Run
tenzro-canton-mcp
```

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `CANTON_API_URL` | `http://localhost:7575` | Canton JSON Ledger API v2 base URL |
| `CANTON_ADMIN_URL` | `http://localhost:7576` | Canton Admin API base URL |
| `CANTON_AUTH_TOKEN` | (none) | Optional JWT bearer token for authentication |
| `MCP_HOST` | `0.0.0.0` | Server bind host |
| `MCP_PORT` | `3005` | Server bind port |

## API Endpoints Used

- **JSON Ledger API v2**: `/v2/commands/submit-and-wait-for-transaction`, `/v2/state/active-contracts`, `/v2/events/events-by-contract-id`, `/v2/updates/transaction-by-id`, `/v2/parties/allocate`, `/v2/parties`, `/v2/packages/upload-dar`
- **Admin API**: `/admin/synchronizer/domains`, `/admin/synchronizer/{id}/fee-schedule`
- **Health**: `/health`

## License

Apache-2.0
