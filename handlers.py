"""Chat functions for the capability-aware Infor Connector (ION API Gateway).

Every handler resolves the target connection explicitly and treats ION paths
as potentially unavailable/partner-documented until a real call confirms them.
"""
from __future__ import annotations

import json
import uuid

from imperal_sdk import ActionResult

import infor_client as ic
from app import chat
from schemas import (
    AccessAudit, ActionOutcome, ActionWorkflowTaskParams, AuditAccessParams,
    CallIonApiParams, ConnectInforParams, ConnectionList, ConnectionRefParams,
    DeleteResult, DisconnectInforParams, DocumentFlowMessage, DocumentFlowMessageList,
    GetDocumentFlowMessageParams, GetWorkflowTaskParams, InforConnection, IonApiResult,
    ListDocumentFlowMessagesParams, ListWorkflowTasksParams, NoParams, PathCheck,
    ResendDocumentFlowMessageParams, WorkflowTask, WorkflowTaskList,
)

_SECRET_NAME = "infor_connections"

_DEFAULT_PROBE_PATHS = [
    "IONSERVICES/api/version",
    "IONSERVICES/api/workflow/tasks",
    "IONSERVICES/api/documentflow/messages",
]


async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_SECRET_NAME)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


async def _save_connections(ctx, connections: list[dict]) -> None:
    await ctx.secrets.set(_SECRET_NAME, json.dumps(connections))


def _connection_entity(connection: dict) -> InforConnection:
    label = connection.get("label") or connection.get("tenant_id", "")
    return InforConnection(
        id=connection.get("id", ""), title=label, label=label,
        portal_url=connection.get("portal_url", ""),
        tenant_id=connection.get("tenant_id", ""), connected=True,
    )


def _find_connection(connections: list[dict], connection_id: str) -> dict | None:
    if not connections:
        return None
    if not connection_id:
        return connections[0]
    for connection in connections:
        if connection.get("id") == connection_id:
            return connection
    return None


async def _resolve_client(ctx, connection_id: str) -> tuple[dict, ic.InforClient]:
    connections = await _load_connections(ctx)
    connection = _find_connection(connections, connection_id)
    if not connection:
        raise ic.InforError("No Infor ION tenant connected yet. Call connect_infor first.")
    client = ic.InforClient(
        portal_url=connection.get("portal_url", ""),
        tenant_id=connection.get("tenant_id", ""),
        client_id=connection.get("client_id", ""),
        client_secret=connection.get("client_secret", ""),
        saak=connection.get("saak", ""),
        sask=connection.get("sask", ""),
    )
    return connection, client


@chat.function("connect_infor", "Connect an Infor OS tenant's ION API Gateway (service-account OAuth2), after validating connectivity.", action_type="write", chain_callable=True, data_model=InforConnection, event="infor-connector.connect_infor", effects=["infor.provider.connected"])
async def connect_infor(ctx, params: ConnectInforParams) -> ActionResult:
    """Imperal action: connect_infor."""
    client = ic.InforClient(
        portal_url=params.portal_url, tenant_id=params.tenant_id,
        client_id=params.client_id, client_secret=params.client_secret,
        saak=params.saak, sask=params.sask,
    )
    try:
        await client._get_token()
    except ic.InforError as exc:
        return ActionResult.error(str(exc), code="INFOR_CONNECT_FAILED", retryable=exc.retryable)
    connections = await _load_connections(ctx)
    connection_id = str(uuid.uuid4())
    record = {
        "id": connection_id, "label": params.label or params.tenant_id,
        "portal_url": client.portal_url, "tenant_id": params.tenant_id,
        "client_id": params.client_id, "client_secret": params.client_secret,
        "saak": params.saak, "sask": params.sask,
    }
    connections.append(record)
    await _save_connections(ctx, connections)
    return ActionResult.success(data=_connection_entity(record), summary="Infor ION tenant connection was verified and saved.")


@chat.function("disconnect_infor", "Disconnect an Infor ION tenant: deletes the saved credentials. Nothing in Infor itself is changed.", action_type="write", chain_callable=True, data_model=DeleteResult, event="infor-connector.disconnect_infor", effects=["infor.provider.disconnected"])
async def disconnect_infor(ctx, params: DisconnectInforParams) -> ActionResult:
    """Imperal action: disconnect_infor."""
    connections = await _load_connections(ctx)
    remaining = [c for c in connections if c.get("id") != params.connection_id]
    if len(remaining) == len(connections):
        return ActionResult.error("That Infor ION tenant connection was not found.", code="INFOR_CONNECTION_NOT_FOUND")
    await _save_connections(ctx, remaining)
    return ActionResult.success(data=DeleteResult(id=params.connection_id, title="Infor connection", deleted=True), summary="Infor ION tenant credentials were removed from Imperal.")


@chat.function("list_connections", "List the connected Infor ION tenants.", action_type="read", chain_callable=True, data_model=ConnectionList, event="infor-connector.list_connections")
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """Imperal action: list_connections."""
    connections = await _load_connections(ctx)
    return ActionResult.success(data=ConnectionList(connections=[_connection_entity(c) for c in connections]), summary="Connections listed.")


@chat.function("call_ion_api", "Make a generic authenticated REST call to any ION-routed path on the connected tenant.", action_type="write", chain_callable=True, data_model=IonApiResult, event="infor-connector.call_ion_api", effects=["update:resource"])
async def call_ion_api(ctx, params: CallIonApiParams) -> ActionResult:
    """Imperal action: call_ion_api."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        body = await client.request(params.method, params.path, params=params.query_params or None, json_body=params.body or None)
    except ic.InforError as exc:
        return ActionResult.error(str(exc), code="INFOR_ION_CALL_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=IonApiResult(id=params.path, title=params.path, status_code=200, body=body), summary="Call ion api done.")


@chat.function("audit_infor_access", "Probe a set of ION paths (defaults to a small common set) and report which respond on this tenant.", action_type="read", chain_callable=True, data_model=AccessAudit, event="infor-connector.audit_infor_access")
async def audit_infor_access(ctx, params: AuditAccessParams) -> ActionResult:
    """Imperal action: audit_infor_access."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
    except ic.InforError as exc:
        return ActionResult.error(str(exc), code="INFOR_NOT_CONNECTED")
    paths = params.paths or _DEFAULT_PROBE_PATHS
    checks: list[PathCheck] = []
    for path in paths:
        try:
            await client.get(path)
            checks.append(PathCheck(path=path, available=True, detail="OK"))
        except ic.InforError as exc:
            checks.append(PathCheck(path=path, available=False, detail=str(exc)))
    return ActionResult.success(data=AccessAudit(id="audit", title="Infor ION access audit", checks=checks), summary="Infor access audit ready.")


@chat.function("list_ion_workflow_tasks", "List ION Workflow tasks visible to this service account, optionally filtered by status.", action_type="read", chain_callable=True, data_model=WorkflowTaskList, event="infor-connector.list_ion_workflow_tasks")
async def list_ion_workflow_tasks(ctx, params: ListWorkflowTasksParams) -> ActionResult:
    """Imperal action: list_ion_workflow_tasks."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        query: dict = {"$top": params.top}
        if params.status:
            query["status"] = params.status
        body = await client.get("IONSERVICES/api/workflow/tasks", params=query)
    except ic.InforError as exc:
        return ActionResult.error(str(exc), code="INFOR_WORKFLOW_LIST_FAILED", retryable=exc.retryable)
    items = body.get("items") or body.get("tasks") or body.get("value") or []
    tasks = [
        WorkflowTask(
            id=str(item.get("id", "")), title=item.get("subject", "") or str(item.get("id", "")),
            subject=item.get("subject", ""), status=item.get("status", ""),
            priority=item.get("priority", ""), due_date=item.get("dueDate", ""), raw=item,
        )
        for item in items if isinstance(item, dict)
    ]
    return ActionResult.success(data=WorkflowTaskList(tasks=tasks), summary="Ion workflow tasks listed.")


@chat.function("get_ion_workflow_task", "Read one ION Workflow task in full by id.", action_type="read", chain_callable=True, data_model=WorkflowTask, event="infor-connector.get_ion_workflow_task")
async def get_ion_workflow_task(ctx, params: GetWorkflowTaskParams) -> ActionResult:
    """Imperal action: get_ion_workflow_task."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.get(f"IONSERVICES/api/workflow/tasks/{params.task_id}")
    except ic.InforError as exc:
        return ActionResult.error(str(exc), code="INFOR_WORKFLOW_GET_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=WorkflowTask(
        id=str(item.get("id", params.task_id)), title=item.get("subject", "") or params.task_id,
        subject=item.get("subject", ""), status=item.get("status", ""),
        priority=item.get("priority", ""), due_date=item.get("dueDate", ""), raw=item,
    ), summary="Ion workflow task retrieved.")


@chat.function("action_ion_workflow_task", "Approve, reject, or complete an ION Workflow task.", action_type="write", chain_callable=True, data_model=ActionOutcome, event="infor-connector.action_ion_workflow_task", effects=["infor.workflow_task.actioned"])
async def action_ion_workflow_task(ctx, params: ActionWorkflowTaskParams) -> ActionResult:
    """Imperal action: action_ion_workflow_task."""
    action = params.action.strip().lower()
    if action not in {"approve", "reject", "complete"}:
        return ActionResult.error("action must be one of: approve, reject, complete.", code="INFOR_INVALID_ACTION")
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        await client.post(f"IONSERVICES/api/workflow/tasks/{params.task_id}/{action}", json_body={"comment": params.comment})
    except ic.InforError as exc:
        return ActionResult.error(str(exc), code="INFOR_WORKFLOW_ACTION_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=ActionOutcome(id=params.task_id, title=f"Workflow task {params.task_id}", success=True, detail=f"Task {action}d."), summary="Action ion workflow task done.")


@chat.function("list_document_flow_messages", "List ION Document Flow messages visible to this service account, optionally filtered by status.", action_type="read", chain_callable=True, data_model=DocumentFlowMessageList, event="infor-connector.list_document_flow_messages")
async def list_document_flow_messages(ctx, params: ListDocumentFlowMessagesParams) -> ActionResult:
    """Imperal action: list_document_flow_messages."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        query: dict = {"$top": params.top}
        if params.status:
            query["status"] = params.status
        body = await client.get("IONSERVICES/api/documentflow/messages", params=query)
    except ic.InforError as exc:
        return ActionResult.error(str(exc), code="INFOR_DOCFLOW_LIST_FAILED", retryable=exc.retryable)
    items = body.get("items") or body.get("messages") or body.get("value") or []
    messages = [
        DocumentFlowMessage(
            id=str(item.get("id", "")), title=item.get("documentType", "") or str(item.get("id", "")),
            status=item.get("status", ""), document_type=item.get("documentType", ""),
            timestamp=item.get("timestamp", ""), raw=item,
        )
        for item in items if isinstance(item, dict)
    ]
    return ActionResult.success(data=DocumentFlowMessageList(messages=messages), summary="Document flow messages listed.")


@chat.function("get_document_flow_message", "Read one ION Document Flow message in full by id.", action_type="read", chain_callable=True, data_model=DocumentFlowMessage, event="infor-connector.get_document_flow_message")
async def get_document_flow_message(ctx, params: GetDocumentFlowMessageParams) -> ActionResult:
    """Imperal action: get_document_flow_message."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        item = await client.get(f"IONSERVICES/api/documentflow/messages/{params.message_id}")
    except ic.InforError as exc:
        return ActionResult.error(str(exc), code="INFOR_DOCFLOW_GET_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=DocumentFlowMessage(
        id=str(item.get("id", params.message_id)), title=item.get("documentType", "") or params.message_id,
        status=item.get("status", ""), document_type=item.get("documentType", ""),
        timestamp=item.get("timestamp", ""), raw=item,
    ), summary="Document flow message retrieved.")


@chat.function("resend_document_flow_message", "Resend a failed/stuck ION Document Flow message.", action_type="write", chain_callable=True, data_model=ActionOutcome, event="infor-connector.resend_document_flow_message", effects=["infor.document_flow_message.resent"])
async def resend_document_flow_message(ctx, params: ResendDocumentFlowMessageParams) -> ActionResult:
    """Imperal action: resend_document_flow_message."""
    try:
        _, client = await _resolve_client(ctx, params.connection_id)
        await client.post(f"IONSERVICES/api/documentflow/messages/{params.message_id}/resend")
    except ic.InforError as exc:
        return ActionResult.error(str(exc), code="INFOR_DOCFLOW_RESEND_FAILED", retryable=exc.retryable)
    return ActionResult.success(data=ActionOutcome(id=params.message_id, title=f"Document Flow message {params.message_id}", success=True, detail="Resend requested."), summary="Resend document flow message done.")
