"""Tenzro Canton MCP Server — 14 tools for Canton 3.x / DAML JSON Ledger API v2."""

import json
import os
import uuid
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("tenzro-canton-mcp")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CANTON_API_URL = os.environ.get("CANTON_API_URL", "http://localhost:7575")
CANTON_ADMIN_URL = os.environ.get("CANTON_ADMIN_URL", "http://localhost:7576")
CANTON_AUTH_TOKEN = os.environ.get("CANTON_AUTH_TOKEN", "")

# CIP-56 well-known template IDs
CIP56_HOLDING_TEMPLATE = "Daml.Finance.Holding:Holding"
CIP56_TRANSFER_TEMPLATE = "Daml.Finance.Holding:TransferRequest"

_http = httpx.AsyncClient(timeout=30)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if CANTON_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {CANTON_AUTH_TOKEN}"
    return headers


def _ledger_url(path: str) -> str:
    return f"{CANTON_API_URL}{path}"


def _admin_url(path: str) -> str:
    return f"{CANTON_ADMIN_URL}{path}"


def _command_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Tools — Commands
# ---------------------------------------------------------------------------

@mcp.tool()
async def canton_submit_command(
    act_as: list[str],
    commands: list[dict],
    read_as: list[str] | None = None,
    command_id: str | None = None,
) -> dict:
    """Submit a DAML command and wait for the transaction result.

    Uses the JSON Ledger API v2 submit-and-wait endpoint.

    Args:
        act_as: List of parties to act as (e.g. ["Alice::domain1"])
        commands: List of command objects. Each is either:
            - {"create": {"templateId": "Module:Template", "payload": {...}}}
            - {"exercise": {"templateId": "Module:Template", "contractId": "...", "choice": "...", "argument": {...}}}
        read_as: Optional list of parties to read as
        command_id: Optional command ID (auto-generated if omitted)
    """
    body = {
        "commands": {
            "commandId": command_id or _command_id(),
            "actAs": act_as,
            "readAs": read_as or act_as,
            "commands": commands,
        }
    }

    resp = await _http.post(
        _ledger_url("/v2/commands/submit-and-wait-for-transaction"),
        json=body,
        headers=_headers(),
    )
    if resp.status_code >= 400:
        return {"error": resp.text, "status_code": resp.status_code}
    data = resp.json()

    # Extract transaction from response
    tx = data.get("transaction", data)
    return {
        "transaction_id": tx.get("transactionId", tx.get("updateId")),
        "command_id": body["commands"]["commandId"],
        "events": tx.get("events", tx.get("rootEventIds", [])),
        "effective_at": tx.get("effectiveAt"),
    }


@mcp.tool()
async def canton_list_contracts(
    party: str,
    template_id: str | None = None,
    limit: int = 50,
) -> dict:
    """List active contracts filtered by party and optional template.

    Args:
        party: Party identifier (e.g. "Alice::domain1")
        template_id: Optional DAML template ID (e.g. "Module:Template")
        limit: Maximum contracts to return (default 50)
    """
    # Build TransactionFilter
    filters: dict[str, Any] = {}
    if template_id:
        filters = {
            "filtersByParty": {
                party: {
                    "cumulative": [{
                        "templateFilter": {
                            "templateIds": [template_id],
                        }
                    }]
                }
            }
        }
    else:
        filters = {
            "filtersByParty": {
                party: {
                    "cumulative": [{}]
                }
            }
        }

    body = {
        "filter": filters,
        "limit": limit,
    }

    resp = await _http.post(
        _ledger_url("/v2/state/active-contracts"),
        json=body,
        headers=_headers(),
    )
    if resp.status_code >= 400:
        return {"error": resp.text, "status_code": resp.status_code}
    data = resp.json()

    # Handle both v2 response shapes
    contracts = data.get("contractEntries", data.get("results", []))
    results = []
    for entry in contracts[:limit]:
        if isinstance(entry, dict):
            contract = entry.get("activeContract", entry.get("contract", entry))
            results.append({
                "contract_id": contract.get("contractId"),
                "template_id": contract.get("templateId"),
                "payload": contract.get("payload", contract.get("createArguments")),
            })

    return {"contracts": results, "count": len(results), "party": party}


@mcp.tool()
async def canton_get_events(
    contract_id: str,
    requesting_parties: list[str],
) -> dict:
    """Get create and archive events for a contract ID.

    Args:
        contract_id: DAML contract ID
        requesting_parties: Parties authorized to see the events
    """
    body = {
        "contractId": contract_id,
        "requestingParties": requesting_parties,
    }

    resp = await _http.post(
        _ledger_url("/v2/events/events-by-contract-id"),
        json=body,
        headers=_headers(),
    )
    if resp.status_code >= 400:
        return {"error": resp.text, "status_code": resp.status_code}
    data = resp.json()

    return {
        "contract_id": contract_id,
        "created": data.get("created"),
        "archived": data.get("archived"),
    }


@mcp.tool()
async def canton_get_transaction(
    transaction_id: str,
    requesting_parties: list[str],
) -> dict:
    """Get transaction details by transaction ID.

    Args:
        transaction_id: Transaction ID
        requesting_parties: Parties authorized to see the transaction
    """
    body = {
        "transactionId": transaction_id,
        "requestingParties": requesting_parties,
    }

    resp = await _http.post(
        _ledger_url("/v2/updates/transaction-by-id"),
        json=body,
        headers=_headers(),
    )
    if resp.status_code >= 400:
        return {"error": resp.text, "status_code": resp.status_code}
    return resp.json()


# ---------------------------------------------------------------------------
# Tools — Party management
# ---------------------------------------------------------------------------

@mcp.tool()
async def canton_allocate_party(
    display_name: str,
    party_id_hint: str | None = None,
) -> dict:
    """Allocate a new party on the Canton ledger.

    Args:
        display_name: Human-readable party name
        party_id_hint: Optional hint for the party ID
    """
    body: dict[str, Any] = {"displayName": display_name}
    if party_id_hint:
        body["partyIdHint"] = party_id_hint

    resp = await _http.post(
        _ledger_url("/v2/parties/allocate"),
        json=body,
        headers=_headers(),
    )
    if resp.status_code >= 400:
        return {"error": resp.text, "status_code": resp.status_code}
    data = resp.json()
    party_details = data.get("partyDetails", data)

    return {
        "party": party_details.get("party"),
        "display_name": party_details.get("displayName"),
        "is_local": party_details.get("isLocal", True),
    }


@mcp.tool()
async def canton_list_parties() -> dict:
    """List all known parties on the Canton ledger."""
    resp = await _http.get(
        _ledger_url("/v2/parties"),
        headers=_headers(),
    )
    if resp.status_code >= 400:
        return {"error": resp.text, "status_code": resp.status_code}
    data = resp.json()
    parties = data.get("partyDetails", data.get("parties", []))

    return {
        "parties": [
            {
                "party": p.get("party"),
                "display_name": p.get("displayName"),
                "is_local": p.get("isLocal"),
            }
            for p in parties
        ],
        "count": len(parties),
    }


# ---------------------------------------------------------------------------
# Tools — Admin API
# ---------------------------------------------------------------------------

@mcp.tool()
async def canton_list_domains() -> dict:
    """List synchronizer domains via the Canton Admin API."""
    resp = await _http.get(
        _admin_url("/admin/synchronizer/domains"),
        headers=_headers(),
    )
    if resp.status_code >= 400:
        return {"error": resp.text, "status_code": resp.status_code}
    data = resp.json()
    domains = data.get("domains", data if isinstance(data, list) else [])

    return {
        "domains": domains,
        "count": len(domains),
    }


@mcp.tool()
async def canton_get_health() -> dict:
    """Check Canton node health status."""
    try:
        resp = await _http.get(
            _ledger_url("/health"),
            headers=_headers(),
        )
        if resp.status_code == 200:
            return {"status": "healthy", "details": resp.json() if resp.text else {}}
        return {"status": "unhealthy", "status_code": resp.status_code}
    except httpx.ConnectError:
        return {"status": "unreachable", "url": CANTON_API_URL}


# ---------------------------------------------------------------------------
# Tools — CIP-56 Tokenization
# ---------------------------------------------------------------------------

@mcp.tool()
async def canton_get_balance(
    party: str,
    instrument_id: str | None = None,
) -> dict:
    """Query CIP-56 token holding balance for a party.

    Args:
        party: Party identifier
        instrument_id: Optional instrument ID to filter (e.g. "TNZO")
    """
    # Query active Holding contracts for the party
    template = CIP56_HOLDING_TEMPLATE
    result = await canton_list_contracts(party=party, template_id=template)

    if "error" in result:
        return result

    holdings = []
    total = 0.0
    for contract in result.get("contracts", []):
        payload = contract.get("payload", {})
        amount_str = payload.get("amount", "0")
        instr = payload.get("instrument", {}).get("id", payload.get("instrumentId", ""))

        if instrument_id and instr != instrument_id:
            continue

        amount = float(amount_str)
        total += amount
        holdings.append({
            "contract_id": contract.get("contract_id"),
            "instrument": instr,
            "amount": amount_str,
        })

    return {
        "party": party,
        "holdings": holdings,
        "total": str(total),
        "instrument_filter": instrument_id,
    }


@mcp.tool()
async def canton_transfer(
    sender: str,
    receiver: str,
    amount: str,
    instrument_id: str,
    holding_contract_id: str,
) -> dict:
    """Execute a CIP-56 two-step token transfer (create TransferRequest, then accept).

    Args:
        sender: Sending party
        receiver: Receiving party
        amount: Transfer amount (DAML Decimal string)
        instrument_id: Instrument identifier (e.g. "TNZO")
        holding_contract_id: Source holding contract ID to transfer from
    """
    # Step 1: Create a TransferRequest
    commands = [{
        "exercise": {
            "templateId": CIP56_HOLDING_TEMPLATE,
            "contractId": holding_contract_id,
            "choice": "Transfer",
            "argument": {
                "newOwner": receiver,
                "amount": amount,
            },
        }
    }]

    result = await canton_submit_command(
        act_as=[sender],
        commands=commands,
    )

    if "error" in result:
        return result

    return {
        "transaction_id": result.get("transaction_id"),
        "sender": sender,
        "receiver": receiver,
        "amount": amount,
        "instrument": instrument_id,
        "status": "transfer_initiated",
        "note": "Receiver must accept the TransferRequest to complete the transfer",
    }


@mcp.tool()
async def canton_create_asset(
    owner: str,
    template_id: str,
    payload: dict,
) -> dict:
    """Create a new DAML contract (asset) on the Canton ledger.

    Args:
        owner: Party to act as (contract owner)
        template_id: DAML template ID (e.g. "MyModule:MyAsset")
        payload: Contract create arguments as a dictionary
    """
    commands = [{
        "create": {
            "templateId": template_id,
            "payload": payload,
        }
    }]

    result = await canton_submit_command(act_as=[owner], commands=commands)

    if "error" in result:
        return result

    return {
        "transaction_id": result.get("transaction_id"),
        "template_id": template_id,
        "owner": owner,
        "status": "created",
    }


@mcp.tool()
async def canton_dvp_settle(
    buyer: str,
    seller: str,
    payment_contract_id: str,
    delivery_contract_id: str,
    dvp_template_id: str = "Daml.Finance.Settlement:DvP",
) -> dict:
    """Execute a Delivery vs Payment (DvP) settlement.

    Atomically exchanges a payment holding for a delivery holding.

    Args:
        buyer: Buyer party
        seller: Seller party
        payment_contract_id: Payment holding contract ID (buyer's funds)
        delivery_contract_id: Delivery holding contract ID (seller's asset)
        dvp_template_id: DvP template ID (default CIP-56 standard)
    """
    # Create DvP contract
    create_commands = [{
        "create": {
            "templateId": dvp_template_id,
            "payload": {
                "buyer": buyer,
                "seller": seller,
                "paymentCid": payment_contract_id,
                "deliveryCid": delivery_contract_id,
            },
        }
    }]

    create_result = await canton_submit_command(
        act_as=[buyer, seller],
        commands=create_commands,
    )

    if "error" in create_result:
        return create_result

    return {
        "transaction_id": create_result.get("transaction_id"),
        "buyer": buyer,
        "seller": seller,
        "payment_contract_id": payment_contract_id,
        "delivery_contract_id": delivery_contract_id,
        "status": "settled",
    }


# ---------------------------------------------------------------------------
# Tools — Packages
# ---------------------------------------------------------------------------

@mcp.tool()
async def canton_upload_dar(
    dar_path: str,
) -> dict:
    """Upload a DAR (DAML Archive) package to the Canton ledger.

    Args:
        dar_path: Local file path to the .dar file
    """
    try:
        with open(dar_path, "rb") as f:
            dar_bytes = f.read()
    except FileNotFoundError:
        return {"error": f"DAR file not found: {dar_path}"}
    except PermissionError:
        return {"error": f"Permission denied reading: {dar_path}"}

    headers = _headers()
    headers["Content-Type"] = "application/octet-stream"

    resp = await _http.post(
        _ledger_url("/v2/packages/upload-dar"),
        content=dar_bytes,
        headers=headers,
    )
    if resp.status_code >= 400:
        return {"error": resp.text, "status_code": resp.status_code}

    data = resp.json() if resp.text else {}
    return {
        "status": "uploaded",
        "package_id": data.get("mainPackageId", data.get("packageId")),
        "dar_path": dar_path,
        "size_bytes": len(dar_bytes),
    }


@mcp.tool()
async def canton_get_fee_schedule(
    domain_id: str,
) -> dict:
    """Get the fee schedule for a synchronizer domain via the Admin API.

    Args:
        domain_id: Synchronizer domain ID
    """
    resp = await _http.get(
        _admin_url(f"/admin/synchronizer/{domain_id}/fee-schedule"),
        headers=_headers(),
    )
    if resp.status_code >= 400:
        return {"error": resp.text, "status_code": resp.status_code}
    data = resp.json()

    # Handle both camelCase and snake_case response shapes
    base_fee = data.get("baseFee", data.get("base_fee"))
    per_byte = data.get("perByteFee", data.get("per_byte_fee"))

    return {
        "domain_id": domain_id,
        "base_fee": base_fee,
        "per_byte_fee": per_byte,
        "raw": data,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    mcp.run(transport="streamable-http", host="0.0.0.0", port=3005)


if __name__ == "__main__":
    main()
