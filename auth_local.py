# auth_local.py
import os, jwt
from jwt import InvalidTokenError, ExpiredSignatureError
from fastapi import Request, HTTPException, status

ALGORITHM = os.getenv("AUTH_ALGORITHM", "HS256")
# 둘 중 아무 키나 있으면 사용: JWT_SHARED_SECRET > JWT_SECRET_KEY
JWT_SHARED_SECRET = os.getenv("JWT_SHARED_SECRET") or os.getenv("JWT_SECRET_KEY")
JWT_PUBLIC_KEY   = os.getenv("JWT_PUBLIC_KEY")  # RS256일 때만
JWT_ISSUER   = os.getenv("JWT_ISSUER")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE")
LEEWAY = int(os.getenv("JWT_LEEWAY", "30"))

def _key():
    if ALGORITHM == "HS256":
        if not JWT_SHARED_SECRET:
            raise RuntimeError("Missing JWT_SHARED_SECRET/JWT_SECRET_KEY")
        return JWT_SHARED_SECRET
    if ALGORITHM == "RS256":
        if not JWT_PUBLIC_KEY:
            raise RuntimeError("Missing JWT_PUBLIC_KEY for RS256")
        return JWT_PUBLIC_KEY
    raise RuntimeError(f"Unsupported alg: {ALGORITHM}")

def _bearer(req: Request):
    auth = req.headers.get("authorization") or req.headers.get("Authorization")
    if not auth: return None
    p = auth.split()
    return p[1] if len(p) == 2 and p[0].lower() == "bearer" else None

def decode(token: str):
    kwargs = {"algorithms":[ALGORITHM], "leeway":LEEWAY, "options":{"require":["exp"]}}
    if JWT_ISSUER:   kwargs["issuer"]   = JWT_ISSUER
    if JWT_AUDIENCE: kwargs["audience"] = JWT_AUDIENCE
    return jwt.decode(token, _key(), **kwargs)

async def get_current_user(req: Request) -> str:
    token = _bearer(req)
    if not token:
        raise HTTPException(401, "Missing Bearer token")
    try:
        payload = decode(token)
    except ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except InvalidTokenError as e:
        raise HTTPException(401, f"Invalid token: {e}")
    uid = payload.get("sub") or payload.get("_id") or payload.get("uid")
    if not uid:
        raise HTTPException(401, "Token missing user id")
    return str(uid)
