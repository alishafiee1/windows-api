API reference: `GET http://127.0.0.1:4001/help`

برای کار با فایل‌های محلی فقط از GET استفاده کن.

## خواندن فایل

```
GET http://127.0.0.1:4001/file/read?loc=D%3A%5Cproject%5Cfile.md
```

اگر فایل بزرگ بود (`total_chars > chunk_size`):

```
GET http://127.0.0.1:4001/file/read?loc=D%3A%5Cproject%5Cfile.md&chunk=1
GET http://127.0.0.1:4001/file/read?loc=D%3A%5Cproject%5Cfile.md&chunk=2
```

## همگام‌سازی داده (استریم chunk)

```
# chunk 1
GET /file/sync_data?loc=D%3A%5Cproject%5Cdocs%5Cdesign.md&method=init_sync&payload=[حداکثر 1800 کاراکتر URL-encoded]

# chunk 2 و بعدی
GET /file/sync_data?loc=D%3A%5Cproject%5Cdocs%5Cdesign.md&method=add_chunk&payload=[1800 char]

# آخرین chunk
GET /file/sync_data?loc=D%3A%5Cproject%5Cdocs%5Cdesign.md&method=add_chunk&finalize=true&payload=[بخش آخر]
```

## لیست فایل‌ها

```
GET http://127.0.0.1:4001/file/list?loc=D%3A%5Cproject%5Cdocs&ext=.md
```

## ویرایش جزئی (GET)

ویرایش کوچک — یک درخواست:

```
GET /file/edit?loc=D%3A%5Cproject%5Cfile.md&mode=replace_text&old_text=...&new_text=...
GET /file/edit?loc=D%3A%5Cproject%5Cfile.md&mode=edit_lines&start_line=15&end_line=20&new_text=...
```

ویرایش بزرگ — استریم chunk:

```
# old_text chunk 1
GET /file/edit?loc=...&mode=replace_text&edit_id=abc&chunk_type=old_text&init_chunk=true&payload=part1

# old_text آخر
GET /file/edit?loc=...&mode=replace_text&edit_id=abc&chunk_type=old_text&payload=part2&finalize=true

# new_text chunk 1
GET /file/edit?loc=...&mode=replace_text&edit_id=abc&chunk_type=new_text&init_chunk=true&payload=new1

# new_text آخر (اعمال ویرایش)
GET /file/edit?loc=...&mode=replace_text&edit_id=abc&chunk_type=new_text&payload=new2&finalize=true
```

## نکات

- `loc` باید مسیر absolute باشد (مثل `D:\project\file.md`)
- هر payload حداکثر 1800 کاراکتر
- برای دستورات PowerShell از `GET /run?cmd=...` استفاده کن
- alias قدیمی: `path` به‌جای `loc`، `/file/write` به‌جای `/file/sync_data`
