"""Tenzro Network MCP Server — 104 blockchain tools for AI agents.

Exposes the full Tenzro Network JSON-RPC interface as MCP tools,
enabling AI agents to interact with the Tenzro L1 settlement layer,
manage wallets, stake tokens, bridge cross-chain, run inference,
coordinate agent swarms, and more.
"""

from fastmcp import FastMCP
from .rpc_client import rpc_call, api_call
import json

mcp = FastMCP("Tenzro Network")


# ---------------------------------------------------------------------------
# Wallet & Balance (6 tools)
# ---------------------------------------------------------------------------


@mcp.tool
async def get_balance(address: str) -> str:
    """Get the TNZO token balance for a hex address. Returns the balance in wei."""
    result = await rpc_call("eth_getBalance", [address, "latest"])
    return json.dumps({"address": address, "balance": result})


@mcp.tool
async def create_wallet(key_type: str = "ed25519") -> str:
    """Create a new wallet keypair. key_type can be 'ed25519' or 'secp256k1'."""
    result = await rpc_call("tenzro_createWallet", [key_type])
    return json.dumps(result)


@mcp.tool
async def send_transaction(
    from_addr: str, to_addr: str, amount: str, gas_limit: int = 21000
) -> str:
    """Send a TNZO transfer transaction from one address to another."""
    nonce = await rpc_call("eth_getTransactionCount", [from_addr, "latest"])
    chain_id = await rpc_call("eth_chainId", [])
    tx = {
        "from": from_addr,
        "to": to_addr,
        "value": amount,
        "gas": hex(gas_limit),
        "nonce": nonce,
        "chainId": chain_id,
    }
    result = await rpc_call("eth_sendRawTransaction", [tx])
    return json.dumps({"tx_hash": result})


@mcp.tool
async def request_faucet(address: str) -> str:
    """Request 100 testnet TNZO tokens from the faucet (24h cooldown per address)."""
    result = await rpc_call("tenzro_faucet", {"address": address})
    return json.dumps(result)


@mcp.tool
async def token_balance(address: str) -> str:
    """Get the TNZO token balance for an address via the token subsystem."""
    result = await rpc_call("tenzro_tokenBalance", [address])
    return json.dumps({"address": address, "balance": result})


@mcp.tool
async def total_supply() -> str:
    """Get the total TNZO token supply."""
    result = await rpc_call("tenzro_totalSupply", [])
    return json.dumps({"total_supply": result})


# ---------------------------------------------------------------------------
# Node & Blocks (3 tools)
# ---------------------------------------------------------------------------


@mcp.tool
async def get_node_status() -> str:
    """Get the current node status including block height, peer count, uptime, and role."""
    result = await rpc_call("tenzro_nodeInfo", [])
    return json.dumps(result)


@mcp.tool
async def get_block(height: int) -> str:
    """Get a block by height with its transactions and metadata."""
    result = await rpc_call("eth_getBlockByNumber", [hex(height), False])
    return json.dumps(result)


@mcp.tool
async def get_transaction(tx_hash: str) -> str:
    """Look up a transaction by its hash. Returns type, sender, recipient, amount, and status."""
    result = await rpc_call("eth_getTransactionByHash", [tx_hash])
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Identity (5 tools)
# ---------------------------------------------------------------------------


@mcp.tool
async def register_identity(identity_type: str, display_name: str) -> str:
    """Register a new TDIP identity. identity_type is 'human' or 'machine'."""
    result = await rpc_call(
        "tenzro_registerIdentity", [identity_type, display_name]
    )
    return json.dumps(result)


@mcp.tool
async def resolve_did(did: str) -> str:
    """Resolve a DID to its identity info and delegation scope."""
    result = await rpc_call("tenzro_resolveIdentity", [did])
    return json.dumps(result)


@mcp.tool
async def set_delegation_scope(
    machine_did: str,
    max_transaction_value: int = None,
    allowed_operations: list = None,
) -> str:
    """Set spending limits and allowed operations for a machine DID."""
    params = {"machine_did": machine_did}
    if max_transaction_value is not None:
        params["max_transaction_value"] = max_transaction_value
    if allowed_operations is not None:
        params["allowed_operations"] = allowed_operations
    result = await rpc_call("tenzro_setDelegationScope", params)
    return json.dumps(result)


@mcp.tool
async def set_username(did: str, username: str) -> str:
    """Set a human-readable username for a DID."""
    result = await rpc_call("tenzro_setUsername", [did, username])
    return json.dumps(result)


@mcp.tool
async def resolve_username(username: str) -> str:
    """Resolve a username to its associated DID and identity info."""
    result = await rpc_call("tenzro_resolveUsername", [username])
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Payments (8 tools)
# ---------------------------------------------------------------------------


@mcp.tool
async def create_payment_challenge(
    protocol: str, resource: str, amount: str
) -> str:
    """Create a payment challenge. protocol is 'mpp', 'x402', or 'native'."""
    result = await rpc_call(
        "tenzro_createPaymentChallenge",
        {"protocol": protocol, "resource": resource, "amount": amount},
    )
    return json.dumps(result)


@mcp.tool
async def verify_payment(
    challenge_id: str, protocol: str, payer_did: str, amount: str
) -> str:
    """Verify a payment credential against a challenge and settle on-chain."""
    result = await rpc_call(
        "tenzro_verifyPayment",
        {
            "challenge_id": challenge_id,
            "protocol": protocol,
            "payer_did": payer_did,
            "amount": amount,
        },
    )
    return json.dumps(result)


@mcp.tool
async def list_payment_protocols() -> str:
    """List supported payment protocols (MPP, x402, native) and their capabilities."""
    result = await rpc_call("tenzro_paymentGatewayInfo", [])
    return json.dumps(result)


@mcp.tool
async def settle_payment(
    from_addr: str, to_addr: str, amount: str, service_type: str
) -> str:
    """Settle a payment between two addresses for a given service type."""
    result = await rpc_call(
        "tenzro_settle",
        {
            "from": from_addr,
            "to": to_addr,
            "amount": amount,
            "service_type": service_type,
        },
    )
    return json.dumps(result)


@mcp.tool
async def create_escrow(payer: str, payee: str, amount: str) -> str:
    """Create an escrow between a payer and payee for a specified amount."""
    result = await rpc_call(
        "tenzro_createEscrow",
        {"payer": payer, "payee": payee, "amount": amount},
    )
    return json.dumps(result)


@mcp.tool
async def release_escrow(escrow_id: str) -> str:
    """Release funds held in an escrow to the payee."""
    result = await rpc_call("tenzro_releaseEscrow", [escrow_id])
    return json.dumps(result)


@mcp.tool
async def open_payment_channel(
    sender: str, recipient: str, deposit: str
) -> str:
    """Open an off-chain micropayment channel with an initial deposit."""
    result = await rpc_call(
        "tenzro_openPaymentChannel",
        {"sender": sender, "recipient": recipient, "deposit": deposit},
    )
    return json.dumps(result)


@mcp.tool
async def close_payment_channel(channel_id: str) -> str:
    """Close a micropayment channel and settle the final balances on-chain."""
    result = await rpc_call("tenzro_closePaymentChannel", [channel_id])
    return json.dumps(result)


# ---------------------------------------------------------------------------
# AI Models (10 tools)
# ---------------------------------------------------------------------------


@mcp.tool
async def list_models(category: str = None, name: str = None) -> str:
    """List available AI models. Optionally filter by category or name."""
    params = {}
    if category:
        params["category"] = category
    if name:
        params["name"] = name
    result = await rpc_call(
        "tenzro_listModels", params if params else []
    )
    return json.dumps(result)


@mcp.tool
async def chat_completion(
    model: str,
    message: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    """Send a chat completion request to a served model and return the response."""
    result = await rpc_call(
        "tenzro_chat",
        {
            "model": model,
            "message": message,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
    )
    return json.dumps(result)


@mcp.tool
async def list_model_endpoints() -> str:
    """List active model service endpoints with their API/MCP URLs and status."""
    result = await rpc_call("tenzro_listModelEndpoints", [])
    return json.dumps(result)


@mcp.tool
async def discover_models(
    category: str = None, max_price: float = None
) -> str:
    """Discover models available on the network with optional price filtering."""
    params = {}
    if category:
        params["category"] = category
    if max_price is not None:
        params["max_price"] = max_price
    result = await rpc_call("tenzro_discoverModels", params)
    return json.dumps(result)


@mcp.tool
async def download_model(model_id: str) -> str:
    """Download a model from the registry to the local node."""
    result = await rpc_call("tenzro_downloadModel", [model_id])
    return json.dumps(result)


@mcp.tool
async def serve_model(model_id: str) -> str:
    """Start serving a model for inference on this node."""
    result = await rpc_call("tenzro_serveModel", [model_id])
    return json.dumps(result)


@mcp.tool
async def stop_model(model_id: str) -> str:
    """Stop serving a model on this node."""
    result = await rpc_call("tenzro_stopModel", [model_id])
    return json.dumps(result)


@mcp.tool
async def delete_model(model_id: str) -> str:
    """Delete a downloaded model from the local node."""
    result = await rpc_call("tenzro_deleteModel", [model_id])
    return json.dumps(result)


@mcp.tool
async def get_download_progress(model_id: str) -> str:
    """Check the download progress of a model."""
    result = await rpc_call("tenzro_getDownloadProgress", [model_id])
    return json.dumps(result)


@mcp.tool
async def list_providers(provider_type: str = None) -> str:
    """List registered providers. Optionally filter by type (Validator, ModelProvider, TeeProvider)."""
    params = [provider_type] if provider_type else []
    result = await rpc_call("tenzro_listProviders", params)
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Staking & Governance (7 tools)
# ---------------------------------------------------------------------------


@mcp.tool
async def stake_tokens(amount: str, provider_type: str) -> str:
    """Stake TNZO tokens as a Validator, ModelProvider, or TeeProvider."""
    result = await rpc_call("tenzro_stake", [amount, provider_type])
    return json.dumps(result)


@mcp.tool
async def unstake_tokens(amount: str, provider_type: str) -> str:
    """Unstake TNZO tokens and initiate the unbonding period."""
    result = await rpc_call("tenzro_unstake", [amount, provider_type])
    return json.dumps(result)


@mcp.tool
async def register_provider(provider_type: str, endpoint: str) -> str:
    """Register as a network provider with a service endpoint."""
    result = await rpc_call(
        "tenzro_registerProvider",
        {"provider_type": provider_type, "endpoint": endpoint},
    )
    return json.dumps(result)


@mcp.tool
async def get_provider_stats(address: str = None) -> str:
    """Get provider statistics: served models, inferences, staking totals."""
    params = [address] if address else []
    result = await rpc_call("tenzro_providerStats", params)
    return json.dumps(result)


@mcp.tool
async def list_proposals() -> str:
    """List active governance proposals."""
    result = await rpc_call("tenzro_listProposals", [])
    return json.dumps(result)


@mcp.tool
async def vote_on_proposal(proposal_id: str, vote: str) -> str:
    """Vote on a governance proposal. vote is 'for', 'against', or 'abstain'."""
    result = await rpc_call("tenzro_vote", [proposal_id, vote])
    return json.dumps(result)


@mcp.tool
async def get_voting_power(address: str) -> str:
    """Get the voting power for an address based on staked TNZO."""
    result = await rpc_call("tenzro_getVotingPower", [address])
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Bridge (5 tools)
# ---------------------------------------------------------------------------


@mcp.tool
async def bridge_tokens(
    token: str,
    from_chain: str,
    to_chain: str,
    amount: str,
    recipient: str,
) -> str:
    """Bridge tokens between Tenzro, Ethereum, Solana, or Base via LayerZero/CCIP/deBridge."""
    result = await rpc_call(
        "tenzro_bridgeTokens",
        {
            "token": token,
            "from_chain": from_chain,
            "to_chain": to_chain,
            "amount": amount,
            "recipient": recipient,
        },
    )
    return json.dumps(result)


@mcp.tool
async def get_bridge_routes(from_chain: str, to_chain: str) -> str:
    """Get available bridge routes between two chains with fees and timing."""
    result = await rpc_call(
        "tenzro_getBridgeRoutes", [from_chain, to_chain]
    )
    return json.dumps(result)


@mcp.tool
async def list_bridge_adapters() -> str:
    """List registered bridge adapters (LayerZero, CCIP, deBridge, Canton)."""
    result = await rpc_call("tenzro_listBridgeAdapters", [])
    return json.dumps(result)


@mcp.tool
async def bridge_quote(
    token: str, from_chain: str, to_chain: str, amount: str
) -> str:
    """Get a fee quote for bridging tokens between two chains."""
    result = await rpc_call(
        "tenzro_bridgeQuote",
        {
            "token": token,
            "from_chain": from_chain,
            "to_chain": to_chain,
            "amount": amount,
        },
    )
    return json.dumps(result)


@mcp.tool
async def bridge_with_hook(
    token: str,
    from_chain: str,
    to_chain: str,
    amount: str,
    hook_target: str,
    hook_calldata: str,
) -> str:
    """Bridge tokens with a post-delivery hook to execute a contract call on the destination chain."""
    result = await rpc_call(
        "tenzro_bridgeWithHook",
        {
            "token": token,
            "from_chain": from_chain,
            "to_chain": to_chain,
            "amount": amount,
            "hook_target": hook_target,
            "hook_calldata": hook_calldata,
        },
    )
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Tokens (7 tools)
# ---------------------------------------------------------------------------


@mcp.tool
async def create_token(
    name: str,
    symbol: str,
    decimals: int = 18,
    initial_supply: str = "1000000",
) -> str:
    """Create a new ERC-20 token via the factory and register it in the unified registry."""
    result = await rpc_call(
        "tenzro_createToken",
        {
            "name": name,
            "symbol": symbol,
            "decimals": decimals,
            "initial_supply": initial_supply,
        },
    )
    return json.dumps(result)


@mcp.tool
async def get_token_info(query: str) -> str:
    """Look up a token by symbol, EVM address, or token ID."""
    result = await rpc_call("tenzro_getToken", [query])
    return json.dumps(result)


@mcp.tool
async def list_tokens(vm_type: str = None) -> str:
    """List registered tokens with optional VM type filter (evm, svm, daml)."""
    params = [vm_type] if vm_type else []
    result = await rpc_call("tenzro_listTokens", params)
    return json.dumps(result)


@mcp.tool
async def deploy_contract(
    code: str, contract_type: str = "evm"
) -> str:
    """Deploy bytecode to the EVM, SVM, or DAML runtime."""
    result = await rpc_call(
        "tenzro_deployContract",
        {"code": code, "contract_type": contract_type},
    )
    return json.dumps(result)


@mcp.tool
async def cross_vm_transfer(
    token: str,
    from_addr: str,
    to_addr: str,
    amount: str,
    from_vm: str,
    to_vm: str,
) -> str:
    """Perform an atomic cross-VM token transfer using the TNZO pointer model."""
    result = await rpc_call(
        "tenzro_crossVmTransfer",
        {
            "token": token,
            "from": from_addr,
            "to": to_addr,
            "amount": amount,
            "from_vm": from_vm,
            "to_vm": to_vm,
        },
    )
    return json.dumps(result)


@mcp.tool
async def wrap_tnzo(vm_type: str = "evm") -> str:
    """Wrap native TNZO to its VM representation (no-op in pointer model)."""
    result = await rpc_call("tenzro_wrapTnzo", [vm_type])
    return json.dumps(result)


@mcp.tool
async def get_token_balance(address: str) -> str:
    """Get TNZO balance across all VMs with decimal conversion."""
    result = await rpc_call("tenzro_getTokenBalance", [address])
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Tasks (7 tools)
# ---------------------------------------------------------------------------


@mcp.tool
async def post_task(
    task_type: str, description: str, budget: str
) -> str:
    """Post a new task to the task marketplace."""
    result = await rpc_call(
        "tenzro_postTask",
        {
            "task_type": task_type,
            "description": description,
            "budget": budget,
        },
    )
    return json.dumps(result)


@mcp.tool
async def list_tasks(
    task_type: str = None, status: str = None
) -> str:
    """List tasks in the marketplace. Optionally filter by type or status."""
    params = {}
    if task_type:
        params["task_type"] = task_type
    if status:
        params["status"] = status
    result = await rpc_call(
        "tenzro_listTasks", params if params else []
    )
    return json.dumps(result)


@mcp.tool
async def get_task(task_id: str) -> str:
    """Get details of a specific task by its ID."""
    result = await rpc_call("tenzro_getTask", [task_id])
    return json.dumps(result)


@mcp.tool
async def quote_task(task_id: str, price: str, model: str) -> str:
    """Submit a quote for a task with a proposed price and model."""
    result = await rpc_call(
        "tenzro_quoteTask",
        {"task_id": task_id, "price": price, "model": model},
    )
    return json.dumps(result)


@mcp.tool
async def assign_task(task_id: str, agent_id: str) -> str:
    """Assign a task to a specific agent."""
    result = await rpc_call("tenzro_assignTask", [task_id, agent_id])
    return json.dumps(result)


@mcp.tool
async def complete_task(task_id: str, result_data: str) -> str:
    """Mark a task as complete with the result data."""
    result = await rpc_call(
        "tenzro_completeTask",
        {"task_id": task_id, "result": result_data},
    )
    return json.dumps(result)


@mcp.tool
async def cancel_task(task_id: str) -> str:
    """Cancel a task in the marketplace."""
    result = await rpc_call("tenzro_cancelTask", [task_id])
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Agents (9 tools)
# ---------------------------------------------------------------------------


@mcp.tool
async def register_agent(name: str, capabilities: list[str]) -> str:
    """Register a new AI agent with the specified capabilities."""
    result = await rpc_call(
        "tenzro_registerAgent",
        {"name": name, "capabilities": capabilities},
    )
    return json.dumps(result)


@mcp.tool
async def send_agent_message(
    from_agent: str,
    to_agent: str,
    message_type: str,
    payload: str,
) -> str:
    """Send a message from one agent to another via the A2A protocol."""
    result = await rpc_call(
        "tenzro_sendAgentMessage",
        {
            "from": from_agent,
            "to": to_agent,
            "message_type": message_type,
            "payload": payload,
        },
    )
    return json.dumps(result)


@mcp.tool
async def spawn_agent(
    parent_did: str, name: str, role: str
) -> str:
    """Spawn a child agent from a parent identity with a specific role."""
    result = await rpc_call(
        "tenzro_spawnAgent",
        {"parent_did": parent_did, "name": name, "role": role},
    )
    return json.dumps(result)


@mcp.tool
async def create_swarm(
    orchestrator_did: str, member_count: int
) -> str:
    """Create a multi-agent swarm with the specified number of members."""
    result = await rpc_call(
        "tenzro_createSwarm",
        {
            "orchestrator_did": orchestrator_did,
            "member_count": member_count,
        },
    )
    return json.dumps(result)


@mcp.tool
async def get_swarm_status(swarm_id: str) -> str:
    """Get the current status and member list of an agent swarm."""
    result = await rpc_call("tenzro_getSwarm", [swarm_id])
    return json.dumps(result)


@mcp.tool
async def terminate_swarm(swarm_id: str) -> str:
    """Terminate an agent swarm and release all members."""
    result = await rpc_call("tenzro_terminateSwarm", [swarm_id])
    return json.dumps(result)


@mcp.tool
async def list_agents() -> str:
    """List all registered agents on the network."""
    result = await rpc_call("tenzro_listAgents", [])
    return json.dumps(result)


@mcp.tool
async def get_agent_info(agent_id: str) -> str:
    """Get detailed information about a specific agent."""
    result = await rpc_call("tenzro_getAgentInfo", [agent_id])
    return json.dumps(result)


@mcp.tool
async def deregister_agent(agent_id: str) -> str:
    """Deregister an agent from the network."""
    result = await rpc_call("tenzro_deregisterAgent", [agent_id])
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Agent Templates (7 tools)
# ---------------------------------------------------------------------------


@mcp.tool
async def register_agent_template(
    name: str,
    description: str,
    template_type: str,
    capabilities: list[str],
) -> str:
    """Register a reusable agent template in the marketplace."""
    result = await rpc_call(
        "tenzro_registerAgentTemplate",
        {
            "name": name,
            "description": description,
            "template_type": template_type,
            "capabilities": capabilities,
        },
    )
    return json.dumps(result)


@mcp.tool
async def list_agent_templates(template_type: str = None) -> str:
    """List available agent templates. Optionally filter by type."""
    params = [template_type] if template_type else []
    result = await rpc_call("tenzro_listAgentTemplates", params)
    return json.dumps(result)


@mcp.tool
async def get_agent_template(template_id: str) -> str:
    """Get details of a specific agent template."""
    result = await rpc_call("tenzro_getAgentTemplate", [template_id])
    return json.dumps(result)


@mcp.tool
async def search_agent_templates(query: str) -> str:
    """Search agent templates by name or description."""
    result = await rpc_call("tenzro_searchAgentTemplates", [query])
    return json.dumps(result)


@mcp.tool
async def spawn_from_template(template_id: str) -> str:
    """Spawn a new agent from a registered template."""
    result = await rpc_call(
        "tenzro_spawnAgentFromTemplate", [template_id]
    )
    return json.dumps(result)


@mcp.tool
async def rate_template(
    template_id: str, rating: int, review: str = None
) -> str:
    """Rate an agent template (1-5 stars) with an optional text review."""
    params = {"template_id": template_id, "rating": rating}
    if review:
        params["review"] = review
    result = await rpc_call("tenzro_rateAgentTemplate", params)
    return json.dumps(result)


@mcp.tool
async def get_template_stats(template_id: str) -> str:
    """Get usage statistics for an agent template."""
    result = await rpc_call(
        "tenzro_getAgentTemplateStats", [template_id]
    )
    return json.dumps(result)


# ---------------------------------------------------------------------------
# NFTs (6 tools)
# ---------------------------------------------------------------------------


@mcp.tool
async def create_nft_collection(
    name: str, symbol: str, nft_type: str = "erc721"
) -> str:
    """Create a new NFT collection. nft_type is 'erc721' or 'erc1155'."""
    result = await rpc_call(
        "tenzro_createNftCollection",
        {"name": name, "symbol": symbol, "nft_type": nft_type},
    )
    return json.dumps(result)


@mcp.tool
async def mint_nft(
    collection_id: str,
    token_id: str,
    recipient: str,
    metadata_uri: str,
) -> str:
    """Mint a new NFT in a collection to a recipient address."""
    result = await rpc_call(
        "tenzro_mintNft",
        {
            "collection_id": collection_id,
            "token_id": token_id,
            "recipient": recipient,
            "metadata_uri": metadata_uri,
        },
    )
    return json.dumps(result)


@mcp.tool
async def transfer_nft(
    collection_id: str,
    token_id: str,
    from_addr: str,
    to_addr: str,
) -> str:
    """Transfer an NFT from one address to another."""
    result = await rpc_call(
        "tenzro_transferNft",
        {
            "collection_id": collection_id,
            "token_id": token_id,
            "from": from_addr,
            "to": to_addr,
        },
    )
    return json.dumps(result)


@mcp.tool
async def get_nft_info(
    collection_id: str, token_id: str = None
) -> str:
    """Get info about an NFT collection or a specific token within it."""
    params = {"collection_id": collection_id}
    if token_id:
        params["token_id"] = token_id
    result = await rpc_call("tenzro_getNftInfo", params)
    return json.dumps(result)


@mcp.tool
async def list_nft_collections(creator: str = None) -> str:
    """List NFT collections. Optionally filter by creator address."""
    params = [creator] if creator else []
    result = await rpc_call("tenzro_listNftCollections", params)
    return json.dumps(result)


@mcp.tool
async def register_nft_pointer(
    collection_id: str, target_vm: str, target_address: str
) -> str:
    """Register a cross-VM pointer for an NFT collection."""
    result = await rpc_call(
        "tenzro_registerNftPointer",
        {
            "collection_id": collection_id,
            "target_vm": target_vm,
            "target_address": target_address,
        },
    )
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Compliance (3 tools)
# ---------------------------------------------------------------------------


@mcp.tool
async def check_compliance(
    token: str, from_addr: str, to_addr: str, amount: str
) -> str:
    """Check if a token transfer complies with registered compliance rules."""
    result = await rpc_call(
        "tenzro_checkCompliance",
        {
            "token": token,
            "from": from_addr,
            "to": to_addr,
            "amount": amount,
        },
    )
    return json.dumps(result)


@mcp.tool
async def register_compliance(
    token: str, kyc_required: bool, holder_limit: int = None
) -> str:
    """Register compliance rules for a token (KYC requirement, holder limits)."""
    params = {"token": token, "kyc_required": kyc_required}
    if holder_limit is not None:
        params["holder_limit"] = holder_limit
    result = await rpc_call("tenzro_registerCompliance", params)
    return json.dumps(result)


@mcp.tool
async def freeze_address(token: str, address: str) -> str:
    """Freeze an address for a specific token, preventing all transfers."""
    result = await rpc_call("tenzro_freezeAddress", [token, address])
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Canton (3 tools)
# ---------------------------------------------------------------------------


@mcp.tool
async def list_canton_domains() -> str:
    """List available Canton synchronization domains."""
    result = await rpc_call("tenzro_listCantonDomains", [])
    return json.dumps(result)


@mcp.tool
async def list_daml_contracts(domain_id: str) -> str:
    """List active DAML contracts on a Canton domain."""
    result = await rpc_call("tenzro_listDamlContracts", [domain_id])
    return json.dumps(result)


@mcp.tool
async def submit_daml_command(
    domain_id: str, command_type: str, payload: str
) -> str:
    """Submit a DAML command (create or exercise) to a Canton domain."""
    result = await rpc_call(
        "tenzro_submitDamlCommand",
        {
            "domain_id": domain_id,
            "command_type": command_type,
            "payload": payload,
        },
    )
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Verification (1 tool)
# ---------------------------------------------------------------------------


@mcp.tool
async def verify_zk_proof(
    proof: str, proof_type: str, public_inputs: list[str]
) -> str:
    """Verify a zero-knowledge proof (Groth16, PlonK, or STARK) with public inputs."""
    result = await api_call(
        "/api/verify/zk-proof",
        "POST",
        {
            "proof": proof,
            "proof_type": proof_type,
            "public_inputs": public_inputs,
        },
    )
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Events (3 tools)
# ---------------------------------------------------------------------------


@mcp.tool
async def get_events(
    from_block: int = None,
    to_block: int = None,
    event_type: str = None,
) -> str:
    """Get blockchain events with optional block range and type filters."""
    params = {}
    if from_block is not None:
        params["from_block"] = from_block
    if to_block is not None:
        params["to_block"] = to_block
    if event_type:
        params["event_type"] = event_type
    result = await rpc_call("tenzro_getEvents", params)
    return json.dumps(result)


@mcp.tool
async def subscribe_events(filter: str) -> str:
    """Subscribe to real-time blockchain events matching a filter expression."""
    result = await rpc_call("tenzro_subscribeEvents", [filter])
    return json.dumps(result)


@mcp.tool
async def register_webhook(
    url: str, filter: str = None, secret: str = None
) -> str:
    """Register a webhook URL to receive event notifications."""
    params = {"url": url}
    if filter:
        params["filter"] = filter
    if secret:
        params["secret"] = secret
    result = await rpc_call("tenzro_registerWebhook", params)
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Join (1 tool)
# ---------------------------------------------------------------------------


@mcp.tool
async def join_as_participant(display_name: str) -> str:
    """Join the Tenzro network as a participant. Provisions identity, wallet, and hardware profile."""
    result = await rpc_call(
        "tenzro_joinAsMicroNode", {"display_name": display_name}
    )
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Skills Registry (5 tools)
# ---------------------------------------------------------------------------


@mcp.tool
async def list_skills() -> str:
    """List all registered skills in the Tenzro skills registry."""
    result = await rpc_call("tenzro_listSkills", [])
    return json.dumps(result)


@mcp.tool
async def register_skill(
    name: str, category: str, description: str, tags: list[str]
) -> str:
    """Register a new skill in the skills registry."""
    result = await rpc_call(
        "tenzro_registerSkill",
        {
            "name": name,
            "category": category,
            "description": description,
            "tags": tags,
        },
    )
    return json.dumps(result)


@mcp.tool
async def search_skills(query: str) -> str:
    """Search the skills registry by keyword or tag."""
    result = await rpc_call("tenzro_searchSkills", [query])
    return json.dumps(result)


@mcp.tool
async def get_skill(skill_id: str) -> str:
    """Get details of a specific skill by its ID."""
    result = await rpc_call("tenzro_getSkill", [skill_id])
    return json.dumps(result)


@mcp.tool
async def use_skill(skill_id: str, input_data: str) -> str:
    """Invoke a registered skill with the given input data."""
    result = await rpc_call(
        "tenzro_useSkill", {"skill_id": skill_id, "input": input_data}
    )
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Tools Registry (5 tools)
# ---------------------------------------------------------------------------


@mcp.tool
async def list_registered_tools() -> str:
    """List all registered MCP tools in the tools registry."""
    result = await rpc_call("tenzro_listTools", [])
    return json.dumps(result)


@mcp.tool
async def register_tool(
    name: str, tool_type: str, endpoint: str, description: str
) -> str:
    """Register a new tool (MCP server endpoint) in the tools registry."""
    result = await rpc_call(
        "tenzro_registerTool",
        {
            "name": name,
            "tool_type": tool_type,
            "endpoint": endpoint,
            "description": description,
        },
    )
    return json.dumps(result)


@mcp.tool
async def search_tools(query: str) -> str:
    """Search the tools registry by keyword."""
    result = await rpc_call("tenzro_searchTools", [query])
    return json.dumps(result)


@mcp.tool
async def get_tool_info(tool_id: str) -> str:
    """Get details of a specific registered tool by its ID."""
    result = await rpc_call("tenzro_getTool", [tool_id])
    return json.dumps(result)


@mcp.tool
async def use_registered_tool(tool_id: str, input_data: str) -> str:
    """Invoke a registered tool with the given input data."""
    result = await rpc_call(
        "tenzro_useTool", {"tool_id": tool_id, "input": input_data}
    )
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Network (1 tool)
# ---------------------------------------------------------------------------


@mcp.tool
async def get_hardware_profile() -> str:
    """Detect and return the hardware profile of the local node (CPU, RAM, GPU, TEE)."""
    result = await rpc_call("tenzro_hardwareProfile", [])
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Usage (2 tools)
# ---------------------------------------------------------------------------


@mcp.tool
async def get_skill_usage(skill_id: str) -> str:
    """Get usage statistics for a registered skill."""
    result = await rpc_call("tenzro_getSkillUsage", [skill_id])
    return json.dumps(result)


@mcp.tool
async def get_tool_usage(tool_id: str) -> str:
    """Get usage statistics for a registered tool."""
    result = await rpc_call("tenzro_getToolUsage", [tool_id])
    return json.dumps(result)


# ---------------------------------------------------------------------------
# deBridge Cross-Chain (5 tools)
# ---------------------------------------------------------------------------


@mcp.tool
async def debridge_search_tokens(query: str, chain_id: int = None) -> str:
    """Search for tokens available on deBridge DLN. Returns token addresses, symbols, and supported chains."""
    params = {"query": query}
    if chain_id:
        params["chain_id"] = chain_id
    result = await rpc_call("tenzro_debridgeSearchTokens", params)
    return json.dumps(result)


@mcp.tool
async def debridge_get_chains() -> str:
    """Get all blockchain networks supported by deBridge DLN for cross-chain transfers."""
    result = await rpc_call("tenzro_debridgeGetChains", {})
    return json.dumps(result)


@mcp.tool
async def debridge_get_instructions() -> str:
    """Get deBridge operational instructions and guidance for cross-chain transfers."""
    result = await rpc_call("tenzro_debridgeGetInstructions", {})
    return json.dumps(result)


@mcp.tool
async def debridge_create_tx(
    src_chain_id: int,
    dst_chain_id: int,
    src_token: str,
    dst_token: str,
    amount: str,
    recipient: str,
    sender: str = None,
) -> str:
    """Create a cross-chain transaction via deBridge DLN. Returns transaction data ready for signing."""
    params = {
        "src_chain_id": src_chain_id,
        "dst_chain_id": dst_chain_id,
        "src_token": src_token,
        "dst_token": dst_token,
        "amount": amount,
        "recipient": recipient,
    }
    if sender:
        params["sender"] = sender
    result = await rpc_call("tenzro_debridgeCreateTx", params)
    return json.dumps(result)


@mcp.tool
async def debridge_same_chain_swap(
    chain_id: int,
    token_in: str,
    token_out: str,
    amount: str,
    sender: str = None,
) -> str:
    """Execute a same-chain token swap via deBridge without cross-chain bridging."""
    params = {"chain_id": chain_id, "token_in": token_in, "token_out": token_out, "amount": amount}
    if sender:
        params["sender"] = sender
    result = await rpc_call("tenzro_debridgeSameChainSwap", params)
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Tenzro MCP Server")
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "http"],
    )
    parser.add_argument("--port", type=int, default=3001)
    args = parser.parse_args()

    if args.transport == "http":
        mcp.run(transport="http", port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
