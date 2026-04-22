# Tenzro MCP Server

[![License](https://img.shields.io/badge/license-Apache--2.0-green)](../LICENSE)
[![MCP](https://img.shields.io/badge/MCP-2024--11--05-blue)](https://modelcontextprotocol.io)

Tenzro L1 blockchain MCP server — 148 tools for wallets, identity, tokens, NFTs, agents, governance, bridge, AI inference, crypto, TEE, ZK proofs, VRF (RFC 9381), and key custody.

**Live:** `https://mcp.tenzro.network/mcp`

## Tools (148)

| Category | Count | Highlights |
|----------|-------|-----------|
| Wallet & Balance | 6 | create_wallet, get_balance, send_transaction, faucet |
| Identity (TDIP) | 5 | register_identity, resolve_did, set_username |
| Payments | 8 | create_payment_challenge, settle, escrow, payment channels |
| AI Models | 10 | list_models, chat_completion, serve, download |
| Staking & Governance | 7 | stake, unstake, proposals, vote |
| Bridge | 5 | bridge_tokens, quote, routes, adapters |
| Tokens | 7 | create_token, deploy_contract, cross_vm_transfer |
| Tasks | 7 | post_task, list_tasks, quote, assign, complete |
| Agents | 9 | register, spawn, create_swarm, terminate_swarm |
| Agent Templates | 7 | register, list, search, spawn, rate |
| NFTs | 6 | create_collection, mint, transfer, list |
| Compliance | 3 | check, register, freeze |
| Canton | 3 | list_domains, list_contracts, submit_command |
| Verification | 3 | verify_zk_proof, verify_vrf_proof, generate_vrf_proof |
| Events | 3 | get_events, subscribe, register_webhook |
| Network | 1 | get_node_status |
| Blocks | 2 | get_block, get_transaction |
| Skills & Tools Registry | 10 | list, register, search, use |
| Join | 1 | join_as_participant |
| Crypto | 9 | sign_message, verify_signature, encrypt, decrypt, hash, key exchange |
| TEE | 6 | detect_tee, attestation, seal/unseal, list_tee_providers |
| ZK Proofs | 3 | create_zk_proof, generate_proving_key, list_zk_circuits |
| Key Custody | 9 | create_mpc_wallet, keystore, key rotation, sessions, spending limits |
| App/Paymaster | 6 | register_app, user wallets, sponsor_transaction, usage stats |
| Contract ABI | 2 | encode_function, decode_result |
| Streaming | 2 | chat_stream, subscribe_events_stream |

## Quick Start

```bash
pip install -e .
python server.py                          # stdio (Claude Desktop)
python server.py --transport http --port 3001  # Streamable HTTP
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TENZRO_RPC_URL` | `https://rpc.tenzro.network` | Tenzro JSON-RPC |
| `TENZRO_API_URL` | `https://api.tenzro.network` | Tenzro Web API |

## Contact

- [tenzro.com](https://tenzro.com) | [eng@tenzro.com](mailto:eng@tenzro.com) | [github.com/tenzro](https://github.com/tenzro)
