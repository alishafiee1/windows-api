"""Integration tests for de-weaponized file API (new names + legacy aliases)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

from app import app

BASE = Path(__file__).resolve().parent.parent
TEST_FILE = BASE / "test_sync_api.txt"
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

    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
