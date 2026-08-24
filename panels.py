"""Infor Connector panel UI, aligned with UI_INTERFACE_STANDARD.md.

Left sidebar: plain stacked content, no card containers, labelled inputs,
App settings last. Setup instructions live only in the help dialog.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
import handlers as h


def _settings_button() -> ui.UINode:
    return ui.Button(
        "App settings", variant="secondary", size="sm", full_width=True,
        icon="settings", on_click=ui.Call("__panel__infor_settings"),
    )


def _field(label: str, node: ui.UINode) -> ui.UINode:
    return ui.Stack(direction="v", gap=1, align="stretch", children=[
        ui.Text(label, variant="caption"), node,
    ])


def _connect_form() -> ui.UINode:
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Button("How do I get this?", variant="ghost", size="sm", icon="HelpCircle",
                  on_click=ui.Call("__panel__infor_connect_help")),
        ui.Form(action="connect_infor", submit_label="Connect", children=[
            _field("Tenant label", ui.Input(param_name="label", placeholder="e.g. Acme Production")),
            _field("ION portal URL (pu)", ui.Input(param_name="portal_url", placeholder="https://mingle-ionapi.inforcloudsuite.com")),
            _field("ION tenant ID (ti)", ui.Input(param_name="tenant_id", placeholder="ACME_PRD_TENANT")),
            _field("OAuth client ID (cn)", ui.Input(param_name="client_id", placeholder="ACME_PRD_TENANT~xxxxxxxx")),
            _field("OAuth client secret (cs)", ui.Password(param_name="client_secret", placeholder="Client secret from .ionapi")),
            _field("Service account access key (saak)", ui.Input(param_name="saak", placeholder="Service account access key")),
            _field("Service account secret key (sask)", ui.Password(param_name="sask", placeholder="Service account secret key")),
        ]),
    ])


@ext.panel("infor_sidebar", slot="left", title="Infor")
async def infor_sidebar(ctx, **kwargs) -> ui.UINode:
    connections = await h._load_connections(ctx)
    if not connections:
        return ui.Stack(direction="v", gap=3, align="stretch", children=[
            ui.Text("Connect your Infor OS tenant to call ION-routed endpoints.", variant="body"),
            _connect_form(),
            ui.Divider(),
            _settings_button(),
        ])
    label = connections[0].get("label") or connections[0].get("tenant_id", "")
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Text(label, variant="subtitle"),
        ui.Text(f"{len(connections)} tenant(s) connected", variant="caption"),
        ui.Divider(),
        ui.Button("Open ION bridge", variant="primary", size="sm", full_width=True,
                  icon="Network", on_click=ui.Call("__panel__infor_center")),
        ui.Divider(),
        _settings_button(),
    ])


@ext.panel("infor_connect_help", slot="center", title="Connecting Infor", icon="HelpCircle", center_overlay=True)
async def infor_connect_help(ctx, **kwargs) -> ui.UINode:
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Header(text="How to connect Infor", level=2),
        ui.Text("1. In ION Desk (or Infor Ming.le admin), create a new Service Account and download its .ionapi credential file.", variant="body"),
        ui.Text("2. Open the .ionapi file (it is JSON) and copy: pu (portal url), ti (tenant id), cn (client id), cs (client secret), saak, sask.", variant="body"),
        ui.Text("3. Paste each value into the matching field in the connect form.", variant="body"),
        ui.Alert(
            title="Scope note",
            message="This connector is a generic bridge to ION-routed endpoints (LN, M3, SunSystems, etc). It does not assume any specific path exists on your tenant -- detailed per-product API documentation may require Infor's partner portal.",
            type="warning",
        ),
    ])


@ext.panel("infor_center", slot="center", title="ION API bridge", icon="Network", center_overlay=True)
async def infor_center(ctx, **kwargs) -> ui.UINode:
    connections = await h._load_connections(ctx)
    if not connections:
        return ui.Text("Connect an Infor ION tenant first.", variant="body")
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Header(text="Generic ION API call", level=2, subtitle="Call any ION-routed endpoint your tenant exposes"),
        ui.Form(action="call_ion_api", submit_label="Call", children=[
            _field("Method", ui.Select(param_name="method", options=["GET", "POST", "PUT", "PATCH", "DELETE"], value="GET")),
            _field("ION path", ui.Input(param_name="path", placeholder="IONSERVICES/api/workflow/tasks")),
            _field("Request body (JSON, optional)", ui.Textarea(param_name="body", placeholder="{}")),
        ]),
        ui.Divider(),
        ui.Text("Workflow and Document Flow", variant="subtitle"),
        ui.Stack(direction="h", gap=2, align="stretch", children=[
            ui.Button("List workflow tasks", variant="secondary", size="sm", on_click=ui.Call("list_workflow_tasks")),
            ui.Button("List document flow messages", variant="secondary", size="sm", on_click=ui.Call("list_document_flow_messages")),
        ]),
    ])
