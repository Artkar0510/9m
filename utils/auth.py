import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.settings import settings

_bearer_scheme = HTTPBearer()


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> str:
    token = credentials.credentials
    try:
        response = await request.app.state.http_client.post(
            settings.auth.introspect_url,
            json={"token": token},
            timeout=5.0,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Auth service returned {exc.response.status_code}",
        )
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service unavailable",
        )

    if not data.get("active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return data["sub"]
