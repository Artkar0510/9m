import hashlib
import json
from dataclasses import dataclass

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.settings import settings

_bearer_scheme = HTTPBearer()


@dataclass
class UserInfo:
    user_id: str
    username: str


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


def _cache_key(token: str) -> str:
    return f"auth:token:{hashlib.sha256(token.encode()).hexdigest()}"


async def get_current_user_info(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> UserInfo:
    token = credentials.credentials
    redis = request.app.state.redis

    if redis is not None:
        try:
            cached = await redis.get(_cache_key(token))
            if cached:
                data = json.loads(cached)
                return UserInfo(user_id=data["user_id"], username=data["username"])
        except Exception:
            pass  # Redis unavailable — fall through to auth service

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

    user_id = data["sub"]
    username = data.get("username") or user_id

    if redis is not None:
        try:
            await redis.setex(
                _cache_key(token),
                settings.auth.token_cache_ttl,
                json.dumps({"user_id": user_id, "username": username}),
            )
        except Exception:
            pass  # Redis write failure is non-fatal

    return UserInfo(user_id=user_id, username=username)


async def get_current_user(info: UserInfo = Depends(get_current_user_info)) -> str:
    return info.user_id
