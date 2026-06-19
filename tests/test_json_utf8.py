"""Verify API returns readable UTF-8 instead of \\uXXXX escapes (disabled by default)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app


def test_json_response_preserves_unicode_characters():
  with app.test_client() as client:
    response = client.get("/run", query_string={"cmd": "Write-Output 'سلام'"})
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert app.json.ensure_ascii is False
    assert "\\u0633" not in body
    assert "سلام" in body


if __name__ == "__main__":
  test_json_response_preserves_unicode_characters()
  print("OK: JSON UTF-8 test passed")
