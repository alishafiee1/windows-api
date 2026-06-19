"""Integration tests for de-weaponized file API (new names + legacy aliases)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

from app import app

BASE = Path(__file__).resolve().parent.parent
TEST_FILE = BASE / "test_sync_api.txt"
EDIT_FILE = BASE / "test_edit_api.txt"
TRIGGER_WORDS = (
    "for_ai_assistants",
    "AI should",
    "recommended for AI",
    "automated_client_integration",
    '"AI"',
    "assistant",
    "steps",
    "get_usage_rules",
)


def main():
    with app.test_client() as client:
        help_body = client.get("/help").get_data(as_text=True)
        help_data = client.get("/help").get_json()

        assert "client_integration_guidelines" in help_data
        for word in TRIGGER_WORDS:
            assert word not in help_body, f"trigger word found: {word}"
        print("OK help: neutral wording")

        # new API
        client.get(
            "/file/sync_data",
            query_string={
                "loc": str(TEST_FILE),
                "payload": "Hello ",
                "method": "init_sync",
            },
        )
        r = client.get(
            "/file/sync_data",
            query_string={
                "loc": str(TEST_FILE),
                "payload": "World",
                "method": "add_chunk",
                "finalize": "true",
            },
        )
        assert r.get_json()["finalized"] is True
        print("OK sync_data (new):", r.get_json()["message"])

        # legacy alias
        legacy_file = BASE / "test_legacy_write.txt"
        client.get(
            "/file/write",
            query_string={
                "path": str(legacy_file),
                "content": "Legacy",
                "mode": "overwrite",
                "done": "true",
            },
        )
        r = client.get("/file/read", query_string={"path": str(legacy_file)})
        assert r.get_json()["content"] == "Legacy"
        legacy_file.unlink()
        print("OK write/path (legacy alias)")

        # read with loc and path
        r_loc = client.get("/file/read", query_string={"loc": str(TEST_FILE)})
        r_path = client.get("/file/read", query_string={"path": str(TEST_FILE)})
        assert r_loc.get_json()["content"] == r_path.get_json()["content"] == "Hello World"
        print("OK read: loc and path aliases")

        # list
        r = client.get("/file/list", query_string={"loc": str(BASE), "ext": ".txt"})
        assert r.status_code == 200
        print("OK list: loc param")

        TEST_FILE.unlink()

        _test_file_edit(client)

    print("ALL TESTS PASSED")


def _test_file_edit(client):
    EDIT_FILE.write_text("line1\nline2\nline3\n", encoding="utf-8")

    r = client.get(
        "/file/edit",
        query_string={
            "loc": str(EDIT_FILE),
            "mode": "replace_text",
            "old_text": "line2",
            "new_text": "replaced",
        },
    )
    assert r.status_code == 200
    assert "replaced" in EDIT_FILE.read_text(encoding="utf-8")
    print("OK edit: replace_text")

    r = client.get(
        "/file/edit",
        query_string={
            "loc": str(EDIT_FILE),
            "mode": "replace_text",
            "old_text": "missing",
            "new_text": "x",
        },
    )
    assert r.status_code == 404
    print("OK edit: replace_text not found")

    dup_file = BASE / "test_edit_dup.txt"
    dup_file.write_text("foo bar foo\n", encoding="utf-8")
    r = client.get(
        "/file/edit",
        query_string={
            "loc": str(dup_file),
            "mode": "replace_text",
            "old_text": "foo",
            "new_text": "baz",
        },
    )
    assert r.status_code == 409
    dup_file.unlink()
    print("OK edit: replace_text multi-match")

    EDIT_FILE.write_text("a\nb\nc\nd\n", encoding="utf-8")
    r = client.get(
        "/file/edit",
        query_string={
            "loc": str(EDIT_FILE),
            "mode": "edit_lines",
            "start_line": 2,
            "end_line": 3,
            "new_text": "X\nY\n",
        },
    )
    assert r.status_code == 200
    assert EDIT_FILE.read_text(encoding="utf-8") == "a\nX\nY\nd\n"
    print("OK edit: edit_lines replace")

    r = client.get(
        "/file/edit",
        query_string={
            "loc": str(EDIT_FILE),
            "mode": "edit_lines",
            "start_line": 2,
            "end_line": 2,
            "new_text": "",
        },
    )
    assert r.status_code == 200
    assert EDIT_FILE.read_text(encoding="utf-8") == "a\nY\nd\n"
    print("OK edit: edit_lines delete")

    r = client.get(
        "/file/edit",
        query_string={
            "loc": str(EDIT_FILE),
            "mode": "edit_lines",
            "start_line": 99,
            "end_line": 99,
            "new_text": "z",
        },
    )
    assert r.status_code == 400
    print("OK edit: edit_lines out of bounds")

    edit_id = "neutral-stream-01"
    EDIT_FILE.write_text("chunk-old\n", encoding="utf-8")
    client.get(
        "/file/edit",
        query_string={
            "loc": str(EDIT_FILE),
            "mode": "replace_text",
            "edit_id": edit_id,
            "chunk_type": "old_text",
            "init_chunk": "true",
            "payload": "chunk-old",
            "finalize": "true",
        },
    )
    r = client.get(
        "/file/edit",
        query_string={
            "loc": str(EDIT_FILE),
            "mode": "replace_text",
            "edit_id": edit_id,
            "chunk_type": "new_text",
            "init_chunk": "true",
            "payload": "chunk-new",
            "finalize": "true",
        },
    )
    assert r.status_code == 200
    assert EDIT_FILE.read_text(encoding="utf-8") == "chunk-new\n"
    print("OK edit: replace_text streaming")

    utf_file = BASE / "test_edit_utf8.txt"
    utf_file.write_text("سلام\n", encoding="utf-8")
    r = client.get(
        "/file/edit",
        query_string={
            "loc": str(utf_file),
            "mode": "replace_text",
            "old_text": "سلام",
            "new_text": "درود",
        },
    )
    assert r.status_code == 200
    assert utf_file.read_text(encoding="utf-8") == "درود\n"
    utf_file.unlink()
    print("OK edit: UTF-8")

    EDIT_FILE.unlink()


if __name__ == "__main__":
    main()
