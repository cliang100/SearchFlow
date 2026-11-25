import pytest
from fastapi.testclient import TestClient

from src.searchflow import config
from src.searchflow.main import app

client = TestClient(app)
ADMIN = {"X-Admin-Token": "secret"}


@pytest.fixture
def admin(monkeypatch):
    monkeypatch.setattr(config, "ADMIN_TOKEN", "secret")


def add(url, title, content):
    res = client.post("/documents/", json={"url": url, "title": title, "content": content}, headers=ADMIN)
    assert res.status_code == 201, res.text
    return res.json()


def test_health():
    assert client.get("/health").json()["status"] == "healthy"


def test_writes_disabled_without_admin_token():
    for method, path in [("post", "/documents/"), ("put", "/documents/1"), ("delete", "/documents/1"),
                         ("post", "/search/rebuild-index"), ("post", "/crawler/start")]:
        res = client.request(method.upper(), path, headers=ADMIN, json={})
        assert res.status_code == 403, (path, res.status_code)


def test_wrong_admin_token(admin):
    res = client.post("/search/rebuild-index", headers={"X-Admin-Token": "nope"})
    assert res.status_code == 401


def test_search_and_autocomplete(admin):
    add("https://a.example/1", "Goroutines", "goroutines goroutines channels")
    add("https://a.example/2", None, "goroutines and maps")
    add("https://a.example/3", "Maps", "maps maps maps")

    results = client.get("/search/", params={"q": "goroutines"}).json()
    assert [r["id"] for r in results] == [1, 2]
    assert results[1]["title"] == "https://a.example/2"

    suggestions = client.get("/search/autocomplete", params={"q": "ma"}).json()["suggestions"]
    assert suggestions == ["maps"]


def test_changes_are_searchable_immediately(admin):
    doc = add("https://a.example/1", "One", "unicorn")
    assert len(client.get("/search/", params={"q": "unicorn"}).json()) == 1

    client.put(f"/documents/{doc['id']}", json={"content": "dragon"}, headers=ADMIN)
    assert client.get("/search/", params={"q": "unicorn"}).json() == []
    assert len(client.get("/search/", params={"q": "dragon"}).json()) == 1

    assert client.delete(f"/documents/{doc['id']}", headers=ADMIN).status_code == 204
    assert client.get("/search/", params={"q": "dragon"}).json() == []
    assert client.get(f"/documents/{doc['id']}").status_code == 404


def test_duplicates_rejected(admin):
    add("https://a.example/1", "One", "same text")
    for body in [{"url": "https://a.example/1", "content": "other"}, {"url": "https://a.example/2", "content": "same text"}]:
        assert client.post("/documents/", json=body, headers=ADMIN).status_code == 409


def test_input_validation(admin):
    assert client.get("/search/", params={"q": "  "}).status_code == 400
    assert client.get("/search/", params={"q": "x" * 201}).status_code == 422
    assert client.get("/documents/", params={"limit": 101}).status_code == 422
    assert client.post("/documents/", json={"url": "javascript:alert(1)"}, headers=ADMIN).status_code == 422


@pytest.mark.parametrize("body,status", [
    ({"start_url": "https://example.com", "max_pages": 1000}, 422),
    ({"start_url": "https://example.com", "max_depth": 9}, 422),
    ({"start_url": "ftp://example.com"}, 422),
    ({"start_url": "http://127.0.0.1:8000"}, 400),
    ({"start_url": "http://169.254.169.254/latest/meta-data/"}, 400),
    ({"start_url": "http://10.0.0.5"}, 400),
])
def test_crawl_request_validation(admin, body, status):
    assert client.post("/crawler/start", json=body, headers=ADMIN).status_code == status


def test_ui_has_security_headers():
    res = client.get("/ui")
    assert res.status_code == 200
    assert "default-src 'self'" in res.headers["content-security-policy"]
