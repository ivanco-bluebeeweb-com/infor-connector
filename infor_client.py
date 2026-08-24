"""Thin ION API Gateway REST client for Infor.

Since Infor's per-product schemas (LN/M3/SunSystems) sit behind a partner
portal, this client exposes a generic authenticated call surface plus a
couple of well-documented ION-level collections (Workflow tasks, Document
Flow messages) that Infor documents publicly at the ION OS layer.
"""
from __future__ import annotations

import time
from typing import Any

import httpx


class InforError(RuntimeError):
    """A safe provider-facing error; never includes credentials."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class InforClient:
    """OAuth2 client-credentials REST client for the ION API Gateway."""

    def __init__(
        self,
        portal_url: str,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        saak: str = "",
        sask: str = "",
        *,
        timeout: float = 30.0,
    ):
        self.portal_url = (portal_url or "").strip().rstrip("/")
        if not self.portal_url.startswith("https://"):
            raise InforError("Portal URL (pu) must be an HTTPS host from your .ionapi file.")
        self.tenant_id = (tenant_id or "").strip()
        self.client_id = (client_id or "").strip()
        self.client_secret = client_secret or ""
        self.saak = saak or ""
        self.sask = sask or ""
        self.timeout = timeout
        self._token: str | None = None
        self._token_expiry: float = 0.0

    async def _get_token(self) -> str:
        now = time.time()
        if self._token and now < self._token_expiry - 30:
            return self._token
        token_url = f"{self.portal_url}/{self.tenant_id}/as/token.oauth2"
        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.saak,
            "password": self.sask,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(token_url, data=data)
        if resp.status_code != 200:
            raise InforError(f"ION token request failed ({resp.status_code}). Check tenant id, client id/secret, and service account keys.")
        body = resp.json()
        token = body.get("access_token")
        if not token:
            raise InforError("ION token response did not include an access_token.")
        self._token = token
        self._token_expiry = now + float(body.get("expires_in", 900))
        return token

    async def request(self, method: str, path: str, *, params: dict | None = None, json_body: Any = None) -> dict:
        token = await self._get_token()
        url = path if path.startswith("http") else f"{self.portal_url}/{self.tenant_id}/{path.lstrip('/')}"
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.request(method.upper(), url, params=params, json=json_body, headers=headers)
        if resp.status_code == 401:
            raise InforError("ION API Gateway rejected the request as unauthorized. The service account may lack access to this path.")
        if resp.status_code == 404:
            raise InforError(f"ION path '{path}' was not found on this tenant. It may require partner-portal documentation not covered by this connector, or may not be enabled for your tenant.")
        if resp.status_code >= 400:
            raise InforError(f"ION API Gateway returned {resp.status_code} for '{path}': {resp.text[:300]}")
        if not resp.content:
            return {}
        try:
            return resp.json()
        except ValueError:
            return {"raw_text": resp.text}

    async def get(self, path: str, *, params: dict | None = None) -> dict:
        return await self.request("GET", path, params=params)

    async def post(self, path: str, *, json_body: Any = None) -> dict:
        return await self.request("POST", path, json_body=json_body)
