"""B330: avatar images are served by the API on installs without nginx, and
an <img> request (which cannot carry X-Session-Token) must reach them.

Only GET /uploads/avatars/<user uuid>.<png|jpg|webp|gif> is public: the same
exposure as nginx's public /uploads/ location in production. Anything else
under /uploads stays behind auth, and the mount is read-only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from apps.api.src.middleware.auth import AuthMiddleware, is_public_route  # noqa: E402

UID = "0325d86e-5461-4381-b092-8821cea3d8ca"


@pytest.mark.parametrize("path", [f"/uploads/avatars/{UID}.{e}" for e in ("png", "jpg", "webp", "gif")])
def test_avatar_file_is_public_for_get(path: str) -> None:
    assert is_public_route(path, "GET")


@pytest.mark.parametrize("path,method", [
    (f"/uploads/avatars/{UID}.png", "POST"),               # GET only
    (f"/uploads/avatars/{UID}.png", "DELETE"),
    (f"/uploads/avatars/{UID}.svg", "GET"),                # not an upload type
    (f"/uploads/avatars/{UID}.png.html", "GET"),
    ("/uploads/avatars/not-a-uuid.png", "GET"),
    ("/uploads/avatars/", "GET"),                          # no listing
    (f"/uploads/other/{UID}.png", "GET"),                  # other folders stay private
    (f"/uploads/avatars/../{UID}.png", "GET"),
    (f"/uploads/avatars/x/{UID}.png", "GET"),
])
def test_everything_else_under_uploads_is_not_public(path: str, method: str) -> None:
    assert not is_public_route(path, method)


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("AUTH_REQUIRED", "true")
    (tmp_path / f"{UID}.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 16)
    (tmp_path / "secret.txt").write_text("no")
    app = FastAPI()
    app.add_middleware(AuthMiddleware)
    app.mount("/uploads/avatars", StaticFiles(directory=str(tmp_path)), name="avatars")
    return TestClient(app)


def test_avatar_served_without_a_session(client: TestClient) -> None:
    r = client.get(f"/uploads/avatars/{UID}.png")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/png")


def test_other_files_in_the_folder_need_auth(client: TestClient) -> None:
    assert client.get("/uploads/avatars/secret.txt").status_code == 401


def test_mount_is_read_only(client: TestClient) -> None:
    # Public pattern is GET-only, so a write never reaches the mount.
    assert client.put(f"/uploads/avatars/{UID}.png", content=b"x").status_code == 401
