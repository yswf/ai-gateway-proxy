import time
import asyncio
import logging
from azure.identity.aio import ClientSecretCredential

logger = logging.getLogger("AzureAuth")

class AzureTokenManager:
    """Manages Azure AD tokens for multiple providers/tenants."""
    def __init__(self):
        self._managers: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def get_token(self, tenant_id: str, client_id: str, client_secret: str, scope: str = "https://cognitiveservices.azure.com/.default") -> str:
        cache_key = f"{tenant_id}:{client_id}"
        now = time.time()
        
        async with self._lock:
            if cache_key not in self._managers:
                self._managers[cache_key] = {
                    "credential": ClientSecretCredential(
                        tenant_id=tenant_id,
                        client_id=client_id,
                        client_secret=client_secret
                    ),
                    "token": None,
                    "expires_on": 0
                }
            
            mgr = self._managers[cache_key]
            
            if not mgr["token"] or now >= (mgr["expires_on"] - 60):
                logger.info(f"[Auth] Fetching new Entra ID token for {client_id}")
                token_info = await mgr["credential"].get_token(scope)
                mgr["token"] = token_info.token
                mgr["expires_on"] = token_info.expires_on
                
            return mgr["token"]

    async def close(self):
        for mgr in self._managers.values():
            await mgr["credential"].close()
        self._managers.clear()

azure_token_manager = AzureTokenManager()
