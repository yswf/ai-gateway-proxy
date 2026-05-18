import time
import json
import logging
from typing import AsyncGenerator
import httpx
import re
from app.core.config import settings
from app.services.azure_auth import azure_token_manager

logger = logging.getLogger("ProxyService")

TIMEOUT = httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0)


def _build_headers(headers: dict, api_key: str, is_azure: bool = False, azure_sub_key: str = "") -> dict:
    forward = {
        k: v for k, v in headers.items()
        if k.lower() not in {"host", "content-length", "transfer-encoding", "authorization", "connection"}
    }
    if is_azure:
        forward["Authorization"] = f"Bearer {api_key}"
        if azure_sub_key:
            forward["Ocp-Apim-Subscription-Key"] = azure_sub_key
    else:
        forward["Authorization"] = f"Bearer {api_key}"
    return forward

async def _resolve_target_and_auth(path: str, body: bytes, base_url: str | None, upstream_api_key: str | None, headers: dict) -> tuple[str, dict]:
    _base = (base_url or "https://api.openai.com").rstrip("/")
    _key = upstream_api_key or ""
    
    is_azure = False
    azure_config = None
    
    # Try parsing API key as Azure JSON
    if _key.strip().startswith("{"):
        try:
            config = json.loads(_key)
            if "tenant_id" in config:
                is_azure = True
                azure_config = config
        except Exception:
            pass
            
    if is_azure:
        # Resolve Azure target URL
        if "?" in path:
            path_part, query_part = path.split("?", 1)
        else:
            path_part, query_part = path, ""
            
        clean_path = path_part.lstrip("/")
        
        # Strip v1/ if present
        if clean_path.startswith("v1/"):
            clean_path = clean_path[3:]
            
        api_version = azure_config.get("api_version", "2025-04-01-preview")
        query_suffix = f"{query_part}&api-version={api_version}" if query_part else f"api-version={api_version}"
        
        if clean_path.startswith("openai/"):
            target_url = f"{_base}/{clean_path}?{query_suffix}"
        else:
            model_name = "default"
            content_type = headers.get("content-type", "")
            
            # Extract model name
            if "application/json" in content_type and body:
                try:
                    data = json.loads(body)
                    model_name = data.get("model", model_name)
                except Exception:
                    pass
            elif "multipart/form-data" in content_type and body:
                try:
                    match = re.search(rb'name="model"\r\n\r\n(.*?)\r\n', body)
                    if match:
                        model_name = match.group(1).decode('utf-8').strip()
                except Exception:
                    pass
            
            if clean_path.startswith("models"):
                target_url = f"{_base}/openai/{clean_path}?{query_suffix}"
            else:
                target_url = f"{_base}/openai/deployments/{model_name}/{clean_path}?{query_suffix}"
                
        # Fetch token
        token = await azure_token_manager.get_token(
            tenant_id=azure_config["tenant_id"],
            client_id=azure_config["client_id"],
            client_secret=azure_config["client_secret"]
        )
        forward_headers = _build_headers(headers, token, is_azure=True, azure_sub_key=azure_config.get("subscription_key", ""))
        return target_url, forward_headers
    else:
        # Standard OpenAI routing
        target_url = f"{_base}/{path.lstrip('/')}"
        forward_headers = _build_headers(headers, _key)
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
    target_url, forward_headers = await _resolve_target_and_auth(path, body, base_url, upstream_api_key, headers)

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
        logger.info(f"[Resp] Upstream returned status: {response.status_code}")
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
    target_url, forward_headers = await _resolve_target_and_auth(path, body, base_url, upstream_api_key, headers)
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
                    logger.info(f"[Resp] Upstream stream returned status: {response.status_code}")
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
