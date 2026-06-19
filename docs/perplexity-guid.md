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

## نکات

- `loc` باید مسیر absolute باشد (مثل `D:\project\file.md`)
- هر payload حداکثر 1800 کاراکتر
- برای دستورات PowerShell از `GET /run?cmd=...` استفاده کن
- alias قدیمی: `path` به‌جای `loc`، `/file/write` به‌جای `/file/sync_data`
