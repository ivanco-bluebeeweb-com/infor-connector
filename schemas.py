"""Pydantic input contracts and SDL result entities for Infor Connector."""
from __future__ import annotations

from imperal_sdk import sdl
from pydantic import BaseModel, Field


class NoParams(BaseModel):
    pass


class ConnectionRefParams(BaseModel):
    connection_id: str = Field("", description="Optional saved Infor ION tenant connection ID. Omit to use the first connected tenant.")


class ConnectInforParams(BaseModel):
    label: str = Field("", description="Friendly tenant label, e.g. 'Acme Production'.")
    portal_url: str = Field(..., description="ION portal/token URL (the 'pu' field from your .ionapi file), e.g. https://mingle-ionapi.inforcloudsuite.com.")
    tenant_id: str = Field(..., description="ION tenant ID (the 'ti' field from your .ionapi file).")
    client_id: str = Field(..., description="ION OAuth client ID (the 'cn' field).")
    client_secret: str = Field(..., description="ION OAuth client secret (the 'cs' field).")
    saak: str = Field(..., description="Service account access key (the 'saak' field).")
    sask: str = Field(..., description="Service account secret key (the 'sask' field).")


class DisconnectInforParams(ConnectionRefParams):
    connection_id: str = Field(..., description="Saved Infor ION tenant connection ID to remove from Imperal.")


class CallIonApiParams(ConnectionRefParams):
    method: str = Field("GET", description="HTTP method: GET, POST, PUT, DELETE, PATCH.")
    path: str = Field(..., description="ION-routed path relative to the tenant root, e.g. 'LN/lnapi/ta/...' or 'IONSERVICES/api/...'.")
    query_params: dict = Field(default_factory=dict, description="Optional query string parameters.")
    body: dict = Field(default_factory=dict, description="Optional JSON request body for POST/PUT/PATCH.")


class AuditAccessParams(ConnectionRefParams):
    paths: list[str] = Field(default_factory=list, description="ION paths to probe for availability. Defaults to a small common set if omitted.")


class ListWorkflowTasksParams(ConnectionRefParams):
    status: str = Field("", description="Optional status filter, e.g. 'OPEN', 'COMPLETED'.")
    top: int = Field(50, ge=1, le=200, description="Maximum records to return (1-200).")


class GetWorkflowTaskParams(ConnectionRefParams):
    task_id: str = Field(..., description="ION Workflow task ID.")


class ActionWorkflowTaskParams(ConnectionRefParams):
    task_id: str = Field(..., description="ION Workflow task ID.")
    action: str = Field(..., description="One of: approve, reject, complete.")
    comment: str = Field("", description="Optional comment to attach to the action.")


class ListDocumentFlowMessagesParams(ConnectionRefParams):
    status: str = Field("", description="Optional status filter, e.g. 'ERROR', 'PROCESSED'.")
    top: int = Field(50, ge=1, le=200, description="Maximum records to return (1-200).")


class GetDocumentFlowMessageParams(ConnectionRefParams):
    message_id: str = Field(..., description="Document Flow message ID.")


class ResendDocumentFlowMessageParams(ConnectionRefParams):
    message_id: str = Field(..., description="Document Flow message ID to resend.")


class InforConnection(sdl.Entity):
    id: str
    title: str
    label: str
    portal_url: str
    tenant_id: str
    connected: bool = True


class ConnectionList(sdl.Entity):
    connections: list[InforConnection] = Field(default_factory=list)


class IonApiResult(sdl.Entity):
    id: str
    title: str
    status_code: int = 200
    body: dict = Field(default_factory=dict)


class PathCheck(sdl.Entity):
    path: str
    available: bool
    detail: str = ""


class AccessAudit(sdl.Entity):
    id: str
    title: str
    checks: list[PathCheck] = Field(default_factory=list)


class WorkflowTask(sdl.Entity):
    id: str
    title: str
    subject: str = ""
    status: str = ""
    priority: str = ""
    due_date: str = ""
    raw: dict = Field(default_factory=dict)


class WorkflowTaskList(sdl.Entity):
    tasks: list[WorkflowTask] = Field(default_factory=list)


class DocumentFlowMessage(sdl.Entity):
    id: str
    title: str
    status: str = ""
    document_type: str = ""
    timestamp: str = ""
    raw: dict = Field(default_factory=dict)


class DocumentFlowMessageList(sdl.Entity):
    messages: list[DocumentFlowMessage] = Field(default_factory=list)


class ActionOutcome(sdl.Entity):
    id: str
    title: str
    success: bool = True
    detail: str = ""


class DeleteResult(sdl.Entity):
    id: str
    title: str
    deleted: bool = True
