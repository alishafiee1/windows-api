import requests
import os
import json
import tempfile
import pytest

BASE_URL = "http://127.0.0.1:4001"
TEST_FILE = r"D:\test_windows_api_temp.txt"


def test_help_endpoint():
    """GET /help should return API docs with status ok"""
    r = requests.get(f"{BASE_URL}/help")
    assert r.status_code == 200
    data = r.json()
    assert "endpoints" in data
    assert "version" in data
    assert data["service"] == "windows-local-integration-api"


def test_run_simple_command():
    """GET /run with a simple PowerShell command"""
    r = requests.get(f"{BASE_URL}/run", params={"cmd": "echo hello"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "hello" in data["output"].lower()
    assert data["exit_code"] == 0


def test_run_get_date():
    """GET /run with Get-Date command"""
    r = requests.get(f"{BASE_URL}/run", params={"cmd": "Get-Date"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["output"] is not None


def test_run_post_method():
    """POST /run with JSON body"""
    r = requests.post(
        f"{BASE_URL}/run",
        json={"cmd": "Write-Output 'post-test'"}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "post-test" in data["output"]


def test_run_invalid_command():
    """Running an invalid command should return error status"""
    r = requests.get(f"{BASE_URL}/run", params={"cmd": "not-a-real-command-xyz123"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "error"


def test_file_write_and_read():
    """Write a file then read it back and verify content"""
    content = "Hello from test!\nLine 2"

    w = requests.get(f"{BASE_URL}/file/sync_data", params={
        "loc": TEST_FILE,
        "method": "init_sync",
        "payload": content,
        "finalize": "true"
    })
    assert w.status_code == 200
    assert w.json()["status"] == "ok"

    r = requests.get(f"{BASE_URL}/file/read", params={"loc": TEST_FILE})
    assert r.status_code == 200
    rdata = r.json()
    assert rdata["status"] == "ok"
    assert "Hello from test" in rdata["content"]


def test_file_list():
    """List files in a known directory"""
    r = requests.get(f"{BASE_URL}/file/list", params={
        "loc": r"D:\2 Curent project git\windows-api"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    names = [i["name"] for i in data["items"]]
    assert "app.py" in names
    assert "config.py" in names


def test_file_list_with_ext_filter():
    """Filter files by .py extension"""
    r = requests.get(f"{BASE_URL}/file/list", params={
        "loc": r"D:\2 Curent project git\windows-api",
        "ext": ".py"
    })
    assert r.status_code == 200
    data = r.json()
    for item in data["items"]:
        if item["type"] == "file":
            assert item["extension"] == ".py"


def test_blocklist_endpoint():
    """GET /blocklist should return valid JSON"""
    r = requests.get(f"{BASE_URL}/blocklist")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, (dict, list))


def test_root_redirects_to_help():
    """GET / should redirect to /help"""
    r = requests.get(f"{BASE_URL}/", allow_redirects=True)
    assert r.status_code == 200
    assert "endpoints" in r.json()


def test_run_missing_cmd_param():
    """GET /run without cmd should return 400 or error"""
    r = requests.get(f"{BASE_URL}/run")
    assert r.status_code in (400, 422, 500) or r.json().get("status") == "error"


def test_utf8_in_command_output():
    """Commands with unicode chars should return valid JSON"""
    r = requests.get(f"{BASE_URL}/run", params={"cmd": "Write-Output 'سلام'"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("ok", "error")


if __name__ == "__main__":
    import sys
    pytest.main([sys.argv[0], "-v"])
