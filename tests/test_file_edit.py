"""Tests for GET /file/edit (fast path and streaming chunks)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

import pytest

from app import app

BASE = Path(__file__).resolve().parent.parent
TEST_FILE = BASE / "test_file_edit_main.txt"


@pytest.fixture
def client():
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_test_file():
    TEST_FILE.write_text(
        "Line 1: Hello\nLine 2: World\nLine 3: Test\nLine 4: Data\n",
        encoding="utf-8",
    )
    yield
    if TEST_FILE.exists():
        TEST_FILE.unlink()


def _send_edit_chunks(client, loc, mode, edit_id, chunk_type, parts, finalize_last=True):
    for index, part in enumerate(parts):
        is_last = index == len(parts) - 1
        response = client.get(
            "/file/edit",
            query_string={
                "loc": loc,
                "mode": mode,
                "edit_id": edit_id,
                "chunk_type": chunk_type,
                "init_chunk": "true" if index == 0 else "false",
                "payload": part,
                "finalize": "true" if is_last and finalize_last else "false",
            },
        )
        assert response.status_code == 200, response.get_json()
    return response


def test_replace_text_fast_path(client):
    response = client.get(
        "/file/edit",
        query_string={
            "loc": str(TEST_FILE),
            "mode": "replace_text",
            "old_text": "Line 2: World",
            "new_text": "Line 2: Edited",
        },
    )
    assert response.status_code == 200
    content = TEST_FILE.read_text(encoding="utf-8")
    assert "Line 2: Edited" in content
    assert "Line 2: World" not in content


def test_replace_text_streaming(client):
    edit_id = "stream-replace-01"
    _send_edit_chunks(
        client, str(TEST_FILE), "replace_text", edit_id, "old_text", ["Line 2: ", "World"]
    )
    response = _send_edit_chunks(
        client, str(TEST_FILE), "replace_text", edit_id, "new_text", ["Line 2: ", "Streamed"]
    )
    assert response.get_json()["message"] == "File updated successfully."
    content = TEST_FILE.read_text(encoding="utf-8")
    assert "Line 2: Streamed" in content
    assert "Line 2: World" not in content


def test_replace_text_not_found(client):
    response = client.get(
        "/file/edit",
        query_string={
            "loc": str(TEST_FILE),
            "mode": "replace_text",
            "old_text": "Non-existent text",
            "new_text": "Should fail",
        },
    )
    assert response.status_code == 404


def test_replace_text_multi_match(client):
    dup_file = BASE / "test_edit_dup.txt"
    dup_file.write_text("foo bar foo\n", encoding="utf-8")
    try:
        response = client.get(
            "/file/edit",
            query_string={
                "loc": str(dup_file),
                "mode": "replace_text",
                "old_text": "foo",
                "new_text": "baz",
            },
        )
        assert response.status_code == 409
    finally:
        dup_file.unlink(missing_ok=True)


def test_edit_lines_fast_path(client):
    response = client.get(
        "/file/edit",
        query_string={
            "loc": str(TEST_FILE),
            "mode": "edit_lines",
            "start_line": 3,
            "end_line": 4,
            "new_text": "Line 3&4: Replaced\n",
        },
    )
    assert response.status_code == 200
    content = TEST_FILE.read_text(encoding="utf-8")
    assert "Line 3&4: Replaced" in content
    assert "Line 4: Data" not in content


def test_edit_lines_streaming(client):
    edit_id = "stream-lines-01"
    response = client.get(
        "/file/edit",
        query_string={
            "loc": str(TEST_FILE),
            "mode": "edit_lines",
            "edit_id": edit_id,
            "chunk_type": "new_text",
            "start_line": 3,
            "end_line": 4,
            "init_chunk": "true",
            "payload": "Line 3&4: ",
            "finalize": "false",
        },
    )
    assert response.status_code == 200

    response = client.get(
        "/file/edit",
        query_string={
            "loc": str(TEST_FILE),
            "mode": "edit_lines",
            "edit_id": edit_id,
            "chunk_type": "new_text",
            "payload": "Streamed\n",
            "finalize": "true",
        },
    )
    assert response.status_code == 200
    content = TEST_FILE.read_text(encoding="utf-8")
    assert "Line 3&4: Streamed" in content


def test_edit_lines_out_of_bounds(client):
    response = client.get(
        "/file/edit",
        query_string={
            "loc": str(TEST_FILE),
            "mode": "edit_lines",
            "start_line": 99,
            "end_line": 99,
            "new_text": "z",
        },
    )
    assert response.status_code == 400


def test_utf8(client):
    utf_file = BASE / "test_edit_utf8.txt"
    utf_file.write_text("سلام\n", encoding="utf-8")
    try:
        response = client.get(
            "/file/edit",
            query_string={
                "loc": str(utf_file),
                "mode": "replace_text",
                "old_text": "سلام",
                "new_text": "درود",
            },
        )
        assert response.status_code == 200
        assert utf_file.read_text(encoding="utf-8") == "درود\n"
    finally:
        utf_file.unlink(missing_ok=True)
