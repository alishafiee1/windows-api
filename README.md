# Windows Local Integration API

> A lightweight Flask-based local REST API that gives AI assistants (like Perplexity, Cursor, etc.) controlled access to your Windows machine - run PowerShell commands, read/write/edit files, and list directories, all over simple HTTP GET requests.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Flask](https://img.shields.io/badge/Flask-3.x-green) ![License: MIT](https://img.shields.io/badge/license-MIT-orange)

---

## 📋 Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Running the Server](#running-the-server)
- [API Reference](#api-reference)
  - [GET /help](#get-help)
  - [GET /run](#get-run)
  - [GET /file/read](#get-fileread)
  - [GET /file/list](#get-filelist)
  - [GET /file/sync_data](#get-filesync_data)
  - [GET /file/edit](#get-fileedit)
  - [GET /blocklist](#get-blocklist)
  - [GET /confirm](#get-confirm)
- [Security](#security)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)
- [Configuration](#configuration)

---

## ✨ Features

- 🖥️ **Run PowerShell commands** and get structured JSON output
- 📄 **Read, write, append, and edit files** with full UTF-8 support
- ✂️ **Surgical file editing** - replace specific text or edit by line range
- 📦 **Chunked streaming** for large content (bypasses URL length limits)
- 📂 **Directory listing** with optional file extension filters
- 🔒 **Localhost-only** access for maximum security
- ⛔ **Command blocklist** to prevent dangerous operations
- ✅ **Human approval mechanism** for sensitive commands

---

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/alishafiee1/windows-api.git
cd windows-api

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
copy env.example .env
```

---

## 🏃 Running the Server

```powershell
python app.py
```

The server starts on `http://127.0.0.1:4001` by default.
Open [http://127.0.0.1:4001/help](http://127.0.0.1:4001/help) to see the full API guide.

---

## 📖 API Reference

### GET /help

Returns the full API documentation as JSON.

```http
GET http://127.0.0.1:4001/help
```

---
### GET /run

Runs a PowerShell command and returns the output as JSON.

```http
GET /run?cmd={command}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `cmd` | string | Yes | PowerShell command to execute |

**Response:**
```json
{ "status": "ok", "output": "...", "exit_code": 0 }
```

> ⚠️ If a command requires approval, status will be `pending` with a `confirm_url`.

---

### GET /file/read

Reads a text file. Supports chunked reading for large files.

```http
GET /file/read?loc=D:\project\file.py
GET /file/read?loc=D:\project\file.py&chunk=1&size=1800
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `loc` | string | Yes | Absolute Windows path to file |
| `chunk` | int | No | Chunk index (1-based) for large files |
| `size` | int | No | Chunk size in chars (default: 1800) |

---

### GET /file/list

Lists files and folders inside a directory.

```http
GET /file/list?loc=D:\project
GET /file/list?loc=D:\project&ext=.py
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `loc` | string | Yes | Absolute path to directory |
| `ext` | string | No | Filter by extension (e.g. `.py`, `.md`) |

---

### GET /file/sync_data

Writes or appends content to a file. Supports streaming large content in multiple chunks.

```http
# Write / overwrite
GET /file/sync_data?loc=D:\file.txt&method=init_sync&payload=Hello World&finalize=true

# Append
GET /file/sync_data?loc=D:\file.txt&method=add_chunk&payload=
More content&finalize=true
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `loc` | string | Yes | Absolute path to target file |
| `method` | string | Yes | `init_sync` (overwrite) or `add_chunk` (append) |
| `payload` | string | Yes | URL-encoded content to write |
| `finalize` | bool | No | Set `true` on last chunk (default: false) |

---

### GET /file/edit

Performs surgical edits on a file. Supports two modes: text replacement and line-based editing.
Also supports **chunked streaming** for large replacements.

#### Fast Path (small payloads)

```http
# Replace specific text
GET /file/edit?loc=D:\file.py&mode=replace_text&old_text=def old()&new_text=def new()

# Edit by line range (replace lines 10-15)
GET /file/edit?loc=D:\file.py&mode=edit_lines&start_line=10&end_line=15&new_text=# replaced

# Delete lines (empty new_text)
GET /file/edit?loc=D:\file.py&mode=edit_lines&start_line=10&end_line=15&new_text=
```

#### Chunked Streaming (large payloads)

For large text blocks, use chunked streaming with `edit_id`:

```http
# 1. Send old_text in chunks
GET /file/edit?loc=...&mode=replace_text&edit_id=abc123&chunk_type=old_text&payload={chunk1}
GET /file/edit?loc=...&mode=replace_text&edit_id=abc123&chunk_type=old_text&payload={chunk2}&finalize=true

# 2. Send new_text in chunks
GET /file/edit?loc=...&mode=replace_text&edit_id=abc123&chunk_type=new_text&payload={chunk1}
GET /file/edit?loc=...&mode=replace_text&edit_id=abc123&chunk_type=new_text&payload={chunk2}&finalize=true
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `loc` | string | Absolute path to file |
| `mode` | string | `replace_text` or `edit_lines` |
| `old_text` | string | (`replace_text`) Text to find |
| `new_text` | string | Replacement text (empty = delete) |
| `start_line` | int | (`edit_lines`) 1-based start line |
| `end_line` | int | (`edit_lines`) 1-based end line |
| `edit_id` | string | Session ID for chunked streaming |
| `chunk_type` | string | `old_text` or `new_text` |
| `finalize` | bool | Commit on last chunk |

---

### GET /blocklist

Returns the list of blocked command patterns.

```http
GET http://127.0.0.1:4001/blocklist
```

---

### GET /confirm

Approves or rejects a pending command.

```http
GET /confirm?token={token}&action=approve
GET /confirm?token={token}&action=reject
```

---

## 🔒 Security

- **Localhost only:** All requests from non-localhost IPs are rejected with `403 Forbidden`.
- **Command blocklist:** Dangerous commands (e.g. `Format-Drive`, `rm -rf`) are blocked immediately.
- **Approval flow:** Sensitive commands trigger a `pending` response requiring explicit human approval via `/confirm`.
- **Path validation:** Only absolute Windows paths are accepted for file operations.
- **File size limit:** Files larger than 2MB cannot be read to prevent memory abuse.

---

## 🧪 Running Tests

```powershell
# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_api_full.py -v
pytest tests/test_file_edit.py -v
```

---

## 📁 Project Structure

```
windows-api/
├── app.py               # Flask app entry point
├── config.py           # Environment configuration
├── requirements.txt   # Python dependencies
├── .env               # Local env vars (not in git)
├── env.example        # Env template
├── routes/
│   ├── help.py        # /help endpoint
│   ├── run.py         # /run endpoint
│   ├── file.py        # /file/* endpoints
│   ├── confirm.py     # /confirm endpoint
│   └── blocklist_route.py # /blocklist endpoint
├── core/
│   ├── edit_buffer.py   # In-memory chunk buffer for /file/edit
│   └── server_lifecycle.py # Server start/stop management
├── data/
│   └── blocklist.txt    # Blocked command patterns
└── tests/
    ├── test_api_full.py   # Full API tests
    ├── test_file_edit.py  # File edit endpoint tests
    ├── test_file_api_neutral.py
    └── test_json_utf8.py
```

---

## ⚙️ Configuration

Copy `env.example` to `.env` and edit the values:

```env
PORT=4001
SHELL=powershell
BLOCKLIST_PATH=data/blocklist.txt
CONFIRM_TIMEOUT=120
```

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `4001` | API server port |
| `SHELL` | `powershell` | Shell used for /run commands |
| `BLOCKLIST_PATH` | `data/blocklist.txt` | Path to blocklist file |
| `CONFIRM_TIMEOUT` | `120` | Seconds before pending command expires |

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

---

## 📄 License

MIT License © 2026 Ali Shafiee
