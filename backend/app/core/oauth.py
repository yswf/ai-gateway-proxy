import msal
from app.core.config import settings


def get_msal_app() -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        client_id=settings.AZURE_CLIENT_ID,
        client_credential=settings.AZURE_CLIENT_SECRET,
        authority=f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}",
    )


SCOPES = ["User.Read"]


def get_auth_url(state: str) -> str:
    app = get_msal_app()
    auth_url = app.get_authorization_request_url(
        scopes=SCOPES,
        state=state,
        redirect_uri=settings.AZURE_REDIRECT_URI,
    )
    return auth_url


def get_token_from_code(code: str) -> dict:
    app = get_msal_app()
    result = app.acquire_token_by_authorization_code(
        code=code,
        scopes=SCOPES,
        redirect_uri=settings.AZURE_REDIRECT_URI,
    )
    return result


def get_user_info(access_token: str) -> dict:
    import httpx
    headers = {"Authorization": f"Bearer {access_token}"}
    response = httpx.get("https://graph.microsoft.com/v1.0/me", headers=headers)
    response.raise_for_status()
    return response.json()
