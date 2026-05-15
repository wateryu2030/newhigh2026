"""微信小程序 code 登录：mock 微信接口与 DuckDB 连接。"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from gateway.app import app

client = TestClient(app)


class _FakeUrlResp:
    def __enter__(self) -> _FakeUrlResp:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps({"openid": "o-test-openid-123", "session_key": "k"}).encode("utf-8")


@pytest.fixture
def _wechat_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WECHAT_MINIPROGRAM_APPID", "wx_test_appid")
    monkeypatch.setenv("WECHAT_MINIPROGRAM_SECRET", "wx_test_secret")


def test_wechat_miniprogram_returns_jwt_with_user_level(
    monkeypatch: pytest.MonkeyPatch, _wechat_env: None
) -> None:
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = None

    with patch(
        "gateway.wechat_auth_routes._open_writable",
        return_value=mock_conn,
    ), patch("urllib.request.urlopen", return_value=_FakeUrlResp()):
        r = client.post("/api/auth/wechat/miniprogram", json={"code": "081234567890abc"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    data = body.get("data") or {}
    token = data.get("token") or data.get("access_token")
    assert token and isinstance(token, str)
    assert data.get("user_level") == "trial"

    from gateway.auth.jwt_auth import verify_token

    pl = verify_token(token)
    assert pl is not None
    assert pl.get("sub")
    assert pl.get("user_level") == "trial"


def test_wechat_miniprogram_code2session_error(monkeypatch: pytest.MonkeyPatch, _wechat_env: None) -> None:
    class _ErrResp:
        def __enter__(self) -> _ErrResp:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"errcode": 40029, "errmsg": "invalid code"}).encode("utf-8")

    with patch("urllib.request.urlopen", return_value=_ErrResp()):
        r = client.post("/api/auth/wechat/miniprogram", json={"code": "badcode"})
    assert r.status_code == 400
    body = r.json()
    assert body.get("ok") is False
