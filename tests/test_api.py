import asyncio
import json
from pathlib import Path

import pytest

from app import app
from datacleaner.engine import MAX_BYTES


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


async def exchange(method, path, body=b""):
    messages = []
    sent = False
    path_only, _, query = path.partition("?")

    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path_only,
        "raw_path": path_only.encode(),
        "root_path": "",
        "query_string": query.encode(),
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8000),
    }
    await app(scope, receive, send)
    start = next(message for message in messages if message["type"] == "http.response.start")
    content = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    headers = dict(start["headers"])
    return start["status"], content, headers


@pytest.mark.parametrize("suffix", ["csv", "xlsx"])
def test_upload_summary_and_both_downloads(suffix):
    example = (EXAMPLES / f"sample_customers.{suffix}").read_bytes()
    status, content, _ = asyncio.run(exchange("POST", f"/api/process?filename=sample_customers.{suffix}", example))
    assert status == 200
    payload = json.loads(content)
    assert payload["summary"] == {"received": 18, "valid": 8, "invalid": 8, "duplicate": 2}

    for key, expected, filename in [
        ("clean", "expected_clean_customers.csv", "clean_customers.csv"),
        ("errors", "expected_errors.csv", "errors.csv"),
    ]:
        status, content, headers = asyncio.run(exchange("GET", payload["downloads"][key]))
        assert status == 200
        assert content == (EXAMPLES / expected).read_bytes()
        assert filename.encode() in headers[b"content-disposition"]


@pytest.mark.parametrize("suffix", ["csv", "xlsx"])
def test_fictional_samples_are_downloadable(suffix):
    status, content, headers = asyncio.run(exchange("GET", f"/api/sample/{suffix}"))
    assert status == 200
    assert content == (EXAMPLES / f"sample_customers.{suffix}").read_bytes()
    assert f"sample_customers.{suffix}".encode() in headers[b"content-disposition"]


def test_oversized_upload_returns_413():
    body = b"x" * (MAX_BYTES + 1)
    status, content, _ = asyncio.run(exchange("POST", "/api/process?filename=large.csv", body))
    assert status == 413
    assert json.loads(content)["detail"]["code"] == "FILE_TOO_LARGE"


def test_invalid_format_and_unreadable_xlsx_are_explained():
    status, content, _ = asyncio.run(exchange("POST", "/api/process?filename=bad.txt", b"bad"))
    assert status == 400
    assert json.loads(content)["detail"]["code"] == "UNSUPPORTED_FORMAT"

    status, content, _ = asyncio.run(exchange("POST", "/api/process?filename=bad.xlsx", b"not an xlsx file"))
    assert status == 400
    assert json.loads(content)["detail"]["code"] == "INVALID_XLSX"


def test_expired_or_unknown_download_returns_404():
    status, content, _ = asyncio.run(exchange("GET", "/api/result/missing/clean"))
    assert status == 404
    assert json.loads(content)["detail"] == "Result expired or not found"