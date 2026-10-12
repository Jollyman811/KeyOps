from starlette.middleware.sessions import SessionMiddleware
from fastapi import Request, HTTPException
from passlib.hash import bcrypt
import time
from itsdangerous import URLSafeSerializer
from .config import settings

def add_session_middleware(app):
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY, session_cookie=settings.SESSION_COOKIE_NAME)

def hash_password(pw: str) -> str:
    return bcrypt.hash(pw)

def verify_password(pw: str, pw_hash: str) -> bool:
    return bcrypt.verify(pw, pw_hash)

def _csrf_serializer():
    return URLSafeSerializer(settings.SECRET_KEY, salt="csrf")

def generate_csrf(request: Request) -> str:
    token = _csrf_serializer().dumps({"uid": request.session.get("uid"), "ts": int(time.time())})
    request.session["_csrf"] = token
    return token

def verify_csrf(request: Request, token: str):
    sess = request.session.get("_csrf")
    if not token or not sess or sess != token:
        raise HTTPException(status_code=403, detail="CSRF invalid")
    try:
        _csrf_serializer().loads(token, max_age=60*60*4)
    except Exception:
        raise HTTPException(status_code=403, detail="CSRF expired/invalid")

from .db import get_session
from .models import User, UserOrg
from typing import Optional

def current_user(request: Request) -> Optional[User]:
    uid = request.session.get("uid")
    if not uid: return None
    with get_session() as s:
        return s.get(User, uid)

def require_login(request: Request) -> User:
    u = current_user(request)
    if not u: raise HTTPException(status_code=401, detail="Login required")
    return u

def current_org_id(request: Request) -> Optional[int]:
    return request.session.get("org_id")

def set_org(request: Request, org_id: int):
    request.session["org_id"] = org_id

def user_role_in_org(user_id: int, org_id: int) -> Optional[str]:
    with get_session() as s:
        uo = s.query(UserOrg).filter(UserOrg.user_id==user_id, UserOrg.org_id==org_id).first()
        return uo.role if uo else None

def require_role(request: Request, role: str):
    u = require_login(request)
    org_id = current_org_id(request)
    if not org_id: raise HTTPException(status_code=400, detail="No org selected")
    r = user_role_in_org(u.id, org_id)
    order = {"owner":3,"admin":2,"member":1}
    if not r or order.get(r,0) < order.get(role,0):
        raise HTTPException(status_code=403, detail="Insufficient role")
