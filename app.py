"""Infor Connector extension declaration.

Infor is a portfolio of vertical CloudSuite products unified by Infor OS. This
connector is a generic, capability-aware bridge to the ION API Gateway --
not a typed per-product (LN/M3/SunSystems) connector, since those schemas
differ per customer and Infor's detailed docs sit behind a partner portal.
"""
from __future__ import annotations

from imperal_sdk import ChatExtension, Extension

ext = Extension(
    "infor-connector",
    version="0.1.0",
    display_name="Infor (ION API Gateway)",
    description=(
        "Connect your own Infor OS tenant via ION API Gateway OAuth2 credentials. "
        "Make generic authenticated REST calls to any ION-routed endpoint across your "
        "licensed Infor CloudSuite products (LN, M3, SunSystems, and others), and "
        "manage ION Workflow tasks and Document Flow messages."
    ),
    icon="icon.svg",
    capabilities=["infor:read", "infor:write"],
    actions_explicit=True,
    system=False,
)

chat = ChatExtension(
    ext,
    tool_name="infor",
    description=(
        "Infor Connector — a generic, capability-aware bridge to a tenant's ION API "
        "Gateway, plus ION Workflow task and Document Flow message management."
    ),
)

ext.secret(
    "infor_connections",
    "JSON list of connected Infor ION API Gateway tenants and encrypted credentials. Managed only through connect_infor and disconnect_infor.",
    required=True,
    write_mode="both",
    max_bytes=65536,
    rotation_hint_days=90,
)(lambda: None)


@ext.health_check
async def health_check(ctx) -> dict:
    """Report whether at least one Infor ION tenant is configured."""
    raw = await ctx.secrets.get("infor_connections")
    import json
    try:
        connections = json.loads(raw) if raw else []
    except (TypeError, ValueError):
        connections = []
    if not connections:
        return {"status": "not_connected", "detail": "No Infor ION tenant connected yet."}
    return {"status": "ok", "detail": f"{len(connections)} Infor ION tenant(s) connected."}
