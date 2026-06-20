---
name: windows-local-integration-api
description: Localhost API for PowerShell commands and file operations via GET. Use when reading, writing, editing, or listing files on this Windows machine through {{base_url}}.
---

# Windows Local Integration API

## Quick start

1. `GET {{base_url}}/help` — returns this guide (markdown).
2. Base URL: `{{base_url}}`
3. All file paths use query param `loc` (alias: `path`) — **absolute Windows paths only**.
4. Prefer GET for file ops; use POST only for `/run` when the command URL exceeds ~2000 chars.

**Valid loc example:** `D:\project\docs\file.md`  
**Invalid:** `docs/file.md`, `./file.md`, `relative/path`

---

## Choose the right endpoint

- **Read a file** → `GET /file/read?loc=...`
- **Edit part of an existing file** → `GET /file/edit` (preferred for updates)
- **Create a new file or replace entire content** → `GET /file/sync_data`
- **List a directory** → `GET /file/list?loc=...`
- **Run PowerShell** → `GET /run?cmd=...` (POST fallback for long commands)
- **Check blocked commands** → `GET /blocklist`
- **Approve a blocked command** → open `confirm_url` from pending response in browser

---

## File read — `GET /file/read`

```http
GET {{base_url}}/file/read?loc=D%3A%5Cproject%5Cfile.md
```

Large files (`total_chars > chunk_size`):

```http
GET {{base_url}}/file/read?loc=...&chunk=1&size={{max_chunk_chars}}
GET {{base_url}}/file/read?loc=...&chunk=2&size={{max_chunk_chars}}
```

| Param | Required | Description |
|-------|----------|-------------|
| `loc` | yes | Absolute file path |
| `chunk` | no | 1-based chunk index |
| `size` | no | Chars per chunk (default {{max_chunk_chars}}) |

---

## Partial edit — `GET /file/edit`

Use for **existing files**. Do not use `/file/sync_data` to patch a file.

### Mode A — fast path (short text, one request)

Estimate URL length first. Persian/Unicode text expands ~3x when URL-encoded. If URL > ~2000 chars, use streaming.

```http
GET {{base_url}}/file/edit?loc=D%3A%5Cproject%5Cfile.md&mode=replace_text&old_text=OLD&new_text=NEW

GET {{base_url}}/file/edit?loc=D%3A%5Cproject%5Cfile.md&mode=edit_lines&start_line=15&end_line=20&new_text=NEW_LINES
```

- `replace_text` — exact match; fails with 409 if `old_text` appears more than once
- `edit_lines` — replaces lines `start_line`..`end_line` (1-indexed, inclusive); empty `new_text` deletes lines

### Mode B — streaming (long text)

**Every chunk request must include:** `loc`, `mode`, `edit_id`, `chunk_type`, `payload`

`finalize` is a **query parameter** (`finalize=true`), not a `method` value.

**replace_text workflow:**

```http
# old_text chunk 1
GET {{base_url}}/file/edit?loc=...&mode=replace_text&edit_id=e1&chunk_type=old_text&init_chunk=true&payload=PART1&finalize=false

# old_text last (close old buffer)
GET {{base_url}}/file/edit?loc=...&mode=replace_text&edit_id=e1&chunk_type=old_text&payload=PART2&finalize=true

# new_text chunk 1
GET {{base_url}}/file/edit?loc=...&mode=replace_text&edit_id=e1&chunk_type=new_text&init_chunk=true&payload=NEW1&finalize=false

# new_text last (apply edit to file)
GET {{base_url}}/file/edit?loc=...&mode=replace_text&edit_id=e1&chunk_type=new_text&payload=NEW2&finalize=true
```

**edit_lines workflow:** stream only `chunk_type=new_text`; set `start_line` and `end_line` on first or final chunk; `finalize=true` on last chunk applies the edit.

---

## Full file write — `GET /file/sync_data`

Use only for **new files** or **full content replacement**. Alias route: `/file/write`.

### Valid `method` values (only two)

- `init_sync` — first chunk (creates/clears file). Legacy alias: `mode=overwrite`
- `add_chunk` — append next chunk. Legacy alias: `mode=append`

### Ending a sync

```http
GET {{base_url}}/file/sync_data?loc=...&method=add_chunk&finalize=true&payload=LAST_PART
```

**Each chunk is written to disk immediately.** `finalize=true` only changes the response message to `"Sync complete."` — it is not a separate commit step.

```http
# chunk 1
GET {{base_url}}/file/sync_data?loc=D%3A%5Cproject%5Cdesign.md&method=init_sync&payload=PART1

# chunk 2
GET {{base_url}}/file/sync_data?loc=...&method=add_chunk&payload=PART2

# last
GET {{base_url}}/file/sync_data?loc=...&method=add_chunk&finalize=true&payload=PART3
```

Legacy aliases: `content` → `payload`, `done` → `finalize`

---

## List directory — `GET /file/list`

```http
GET {{base_url}}/file/list?loc=D%3A%5Cproject%5Cdocs&ext=.md
```

| Param | Required | Description |
|-------|----------|-------------|
| `loc` | yes | Absolute directory path |
| `ext` | no | Filter by extension, e.g. `.md` |

---

## Shell commands — `GET /run`

```http
GET {{base_url}}/run?cmd=Get-Date
```

URL-encode the command (`%20` for spaces, `%5C` for backslashes).

**POST fallback** (long commands):

```http
POST {{base_url}}/run
Content-Type: application/json

{"cmd": "your PowerShell command"}
```

### Response handling

| status | Meaning |
|--------|---------|
| `ok` | Success — read `output` |
| `error` | Failed — read `error` |
| `pending` | Blocklist match — open `confirm_url` in browser for approval |
| `timeout` | Command exceeded 30s limit |

---

## Blocklist and approval

```http
GET {{base_url}}/blocklist
```

When `/run` returns `status: pending`, the user must approve via the browser URL in `confirm_url`. Tokens expire after `CONFIRM_TIMEOUT` seconds (see `.env`).

---

## Common mistakes

**Invalid paths**
- `loc=docs/file.md` → 400 (must be absolute)

**sync_data — invalid method names (all return 400)**
- Do NOT use: `method=sync_finish`, `method=finish`, `method=commit_sync`, `method=finalize_sync`
- Correct close: `method=add_chunk&finalize=true`

**Wrong tool for the job**
- Using `/file/sync_data` to edit part of a file → incomplete or corrupted file
- Use `/file/edit` instead

**edit streaming**
- Sending only `edit_id` without `loc` and `mode` → 400
- Omitting `mode=replace_text` on new_text chunks → 400

---

## Limits

- Host: `127.0.0.1` only (not exposed to network)
- Max read file size: 2 MB
- Max payload per chunk: ~{{max_chunk_chars}} characters
- Approximate max URL length: ~2000 characters
- Command output truncated at 20000 characters
- Shell: PowerShell (`-NoProfile -NonInteractive`)

---

## Endpoint summary

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/help` | This markdown guide |
| GET | `/run` | Run PowerShell command |
| POST | `/run` | Run command (long payload) |
| GET | `/file/read` | Read text file |
| GET | `/file/edit` | Partial file update |
| GET | `/file/sync_data` | Stream-write full file |
| GET | `/file/list` | List directory |
| GET | `/blocklist` | List approval keywords |
| GET | `/confirm/<token>` | Approve/reject command |
