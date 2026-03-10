from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass

from fastapi import HTTPException, Request, Response, WebSocket, status
from itsdangerous import BadSignature, URLSafeSerializer


COOKIE_NAME = "quant_desk_session"


@dataclass(slots=True)
class SessionData:
    subject: str
    csrf_token: str


class SessionManager:
    def __init__(self, secret: str) -> None:
        self.serializer = URLSafeSerializer(secret_key=secret, salt="quant-desk")

    def create_session(self, response: Response, subject: str = "operator") -> SessionData:
        session = SessionData(subject=subject, csrf_token=secrets.token_urlsafe(24))
        token = self.serializer.dumps({"sub": session.subject, "csrf": session.csrf_token})
        response.set_cookie(
            COOKIE_NAME,
            token,
            httponly=True,
            samesite="lax",
            secure=False,
            path="/",
        )
        return session

    def clear_session(self, response: Response) -> None:
        response.delete_cookie(COOKIE_NAME, path="/")

    def read_request_session(self, request: Request) -> SessionData | None:
        token = request.cookies.get(COOKIE_NAME)
        if not token:
            return None
        return self._decode(token)

    def read_websocket_session(self, websocket: WebSocket) -> SessionData | None:
        token = websocket.cookies.get(COOKIE_NAME)
        if not token:
            return None
        return self._decode(token)

    def require_request_session(self, request: Request) -> SessionData:
        session = self.read_request_session(request)
        if session is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
        return session

    def verify_csrf(self, request: Request) -> SessionData:
        session = self.require_request_session(request)
        csrf_header = request.headers.get("x-csrf-token", "")
        if not hmac.compare_digest(csrf_header, session.csrf_token):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token.")
        return session

    def verify_password(self, supplied_password: str, expected_password: str) -> bool:
        return hmac.compare_digest(supplied_password, expected_password)

    def _decode(self, token: str) -> SessionData | None:
        try:
            payload = self.serializer.loads(token)
        except BadSignature:
            return None
        subject = str(payload.get("sub") or "operator")
        csrf = str(payload.get("csrf") or "")
        if not csrf:
            return None
        return SessionData(subject=subject, csrf_token=csrf)
