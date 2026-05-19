import os
import json
import time
import asyncio
import re
import logging
from typing import AsyncGenerator
import httpx
from azure.identity.aio import ClientSecretCredential
from app.core.config import settings

logger = logging.getLogger("ProxyService")

TIMEOUT = httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0)

# ================= 1. Environment Config =================
CLIENT_ID = settings.AZURE_CLIENT_ID
CLIENT_SECRET = settings.AZURE_CLIENT_SECRET
TENANT_ID = settings.AZURE_TENANT_ID
SCOPE = "https://cognitiveservices.azure.com/.default"

# ================= 2. Token Manager =================
class TokenManager:
    def __init__(self):
        self.credential = ClientSecretCredential(
            tenant_id=TENANT_ID,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET
        )
        self.current_token = None
        self.expires_on = 0
        self._lock = asyncio.Lock()

    async def get_token(self):
        now = time.time()
        if not self.current_token or now >= (self.expires_on - 30):
            async with self._lock:
                if not self.current_token or now >= (self.expires_on - 30):
                    logger.info("[Auth] Token expired or missing. Fetching new Entra ID token...")
                    try:
                        token_info = await self.credential.get_token(SCOPE)
                        self.current_token = token_info.token
                        self.expires_on = token_info.expires_on
                        # 将时间戳转换为可读格式打印
                        expire_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.expires_on))
                        logger.info(f"[Auth] Token refreshed successfully. Expires at: {expire_time_str}")
                    except Exception as e:
                        logger.error(f"[Auth] Failed to fetch token: {str(e)}")
                        raise e
        return self.current_token

    async def close(self):
        await self.credential.close()

token_manager = TokenManager()

# ================= 3. Core Logic =================
async def _resolve_target_and_auth(path: str, body: bytes, headers: dict, base_url: str | None = None, upstream_api_key: str | None = None) -> tuple[str, dict]:
    """Resolve the target URL for Azure OpenAI and build the request headers."""
    clean_path = path.lstrip("/")
    
    api_base = (base_url or "").rstrip("/")
    sub_key = upstream_api_key or ""
    
    # Simple pass-through without path manipulation
    target_url = f"{api_base}/{clean_path}"

    # 2. Get Token and build headers
    token = await token_manager.get_token()
    
    forward_headers = {
        "Authorization": f"Bearer {token}",
    }
    
    # Include Subscription key if configured
    if sub_key:
        forward_headers["Ocp-Apim-Subscription-Key"] = sub_key
    
    exclude_headers = {"host", "content-length", "authorization", "connection"}
    for k, v in headers.items():
        if k.lower() not in exclude_headers and k.lower() not in forward_headers:
            forward_headers[k] = v

    return target_url, forward_headers


async def proxy_request(
    path: str,
    method: str,
    headers: dict,
    body: bytes,
    base_url: str | None = None,
    upstream_api_key: str | None = None,
) -> tuple[httpx.Response, int]:
    """Forward a non-streaming request to the upstream API, return (response, latency_ms)."""
    target_url, forward_headers = await _resolve_target_and_auth(path, body, headers, base_url, upstream_api_key)

    logger.info(f"[Fwd ] Forwarding {method} to -> {target_url}")

    start_ms = time.time()
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.request(
                method=method,
                url=target_url,
                headers=forward_headers,
                content=body,
            )
        logger.info(f"[Resp] Azure returned status: {response.status_code}")
    except Exception as e:
        logger.error(f"[Err ] Proxy network error: {str(e)}")
        raise e
        
    latency_ms = int((time.time() - start_ms) * 1000)
    return response, latency_ms


async def proxy_stream(
    path: str,
    method: str,
    headers: dict,
    body: bytes,
    base_url: str | None = None,
    upstream_api_key: str | None = None,
) -> tuple[AsyncGenerator[bytes, None], float]:
    """Forward a streaming request, return (async_generator, start_time)."""
    target_url, forward_headers = await _resolve_target_and_auth(path, body, headers, base_url, upstream_api_key)
    start_time = time.time()

    logger.info(f"[Fwd ] Forwarding stream {method} to -> {target_url}")

    async def stream_generator():
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            try:
                async with client.stream(
                    method=method,
                    url=target_url,
                    headers=forward_headers,
                    content=body,
                ) as response:
                    logger.info(f"[Resp] Azure stream returned status: {response.status_code}")
                    async for chunk in response.aiter_bytes():
                        yield chunk
            except Exception as stream_err:
                logger.error(f"[Err ] Stream interrupted: {str(stream_err)}")

    return stream_generator(), start_time


async def fetch_provider_models(base_url: str, api_key: str) -> list[dict]:
    """Call the upstream /v1/models endpoint and return raw model objects."""
    target_url = f"{base_url.rstrip('/')}/v1/models"
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
        resp = await client.get(
            target_url,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", [])


def extract_usage_from_response(response_body: bytes) -> dict:
    """Parse token usage from OpenAI JSON response."""
    try:
        data = json.loads(response_body)
        usage = data.get("usage", {})
        return {
            "model": data.get("model", "unknown"),
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }
    except Exception:
        return {
            "model": "unknown",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
