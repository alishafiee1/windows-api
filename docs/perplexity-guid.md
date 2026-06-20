# راهنمای یکپارچه‌سازی — windows-local-integration-api

## شروع (ترتیب اجباری)

```
1. GET http://127.0.0.1:4001/help
2. از JSON فیلد integration_guide_file.read_via را بخوان (URL آماده با مسیر absolute)
   — هرگز relative_loc را مستقیم در loc نگذار
3. این فایل را با همان read_via یا absolute_loc بخوان
```

**قانون طلایی مسیر:** `loc` همیشه مسیر **absolute** ویندوز است.

```
درست:  D:\2 Curent project git\windows-api\docs\perplexity-guid.md
غلط:   docs/perplexity-guid.md
غلط:   ./docs/perplexity-guid.md
```

---

## کدام endpoint برای چه کاری؟

**فایل از قبل وجود دارد و فقط بخشی عوض می‌شود** → `/file/edit`

**فایل جدید یا جایگزینی کامل محتوا** → `/file/sync_data`

**فقط خواندن** → `/file/read`

**لیست پوشه** → `/file/list`

---

## خواندن فایل

```
GET http://127.0.0.1:4001/file/read?loc=D%3A%5Cproject%5Cfile.md
```

فایل بزرگ (`total_chars > chunk_size`):

```
GET .../file/read?loc=...&chunk=1&size=1800
GET .../file/read?loc=...&chunk=2&size=1800
```

---

## ویرایش فایل موجود — `/file/edit` (اولویت)

### روش ۱ — fast path (متن کوتاه، یک درخواست)

```
GET /file/edit?loc=D%3A%5Cproject%5Cfile.md&mode=replace_text&old_text=متن_قدیم&new_text=متن_جدید

GET /file/edit?loc=D%3A%5Cproject%5Cfile.md&mode=edit_lines&start_line=15&end_line=20&new_text=...
```

قبل از fast path طول `old_text` و `new_text` را تخمین بزن. متن فارسی URL-encoded حدود ۳ برابر طول ظاهری می‌شود. اگر URL از ~۲۰۰۰ کاراکتر بیشتر شد → streaming.

### روش ۲ — streaming (متن بلند)

**در هر chunk این پارامترها الزامی‌اند:** `loc` + `mode` + `edit_id` + `chunk_type` + `payload`

```
# old_text — chunk 1
GET /file/edit?loc=D%3A%5Cfile.md&mode=replace_text&edit_id=e1&chunk_type=old_text&init_chunk=true&payload=بخش۱&finalize=false

# old_text — آخر (بستن buffer قدیم)
GET /file/edit?loc=D%3A%5Cfile.md&mode=replace_text&edit_id=e1&chunk_type=old_text&payload=بخش۲&finalize=true

# new_text — chunk 1
GET /file/edit?loc=D%3A%5Cfile.md&mode=replace_text&edit_id=e1&chunk_type=new_text&init_chunk=true&payload=جدید۱&finalize=false

# new_text — آخر (اعمال ویرایش روی فایل)
GET /file/edit?loc=D%3A%5Cfile.md&mode=replace_text&edit_id=e1&chunk_type=new_text&payload=جدید۲&finalize=true
```

`finalize` یک **query parameter** است (`finalize=true`) — نه مقدار `method`.

---

## نوشتن فایل جدید یا جایگزینی کامل — `/file/sync_data`

فقط وقتی کل فایل را از صفر می‌نویسی. برای ویرایش بخشی از فایل از `/file/edit` استفاده کن.

### فقط دو مقدار برای `method`

- `init_sync` — chunk اول (فایل پاک و از نو)
- `add_chunk` — chunk بعدی (append)

### پایان sync

```
method=add_chunk&finalize=true&payload=آخرین_بخش
```

**هر chunk بلافاصله روی دیسک نوشته می‌شود.** `finalize=true` فقط در JSON پاسخ `"Sync complete."` برمی‌گرداند — شرط ذخیره نیست.

### مثال کامل

```
# chunk 1
GET /file/sync_data?loc=D%3A%5Cproject%5Cdesign.md&method=init_sync&payload=بخش۱

# chunk 2
GET /file/sync_data?loc=D%3A%5Cproject%5Cdesign.md&method=add_chunk&payload=بخش۲

# آخر
GET /file/sync_data?loc=D%3A%5Cproject%5Cdesign.md&method=add_chunk&finalize=true&payload=بخش۳
```

---

## لیست فایل‌ها

```
GET http://127.0.0.1:4001/file/read?loc=...   ← فایل
GET http://127.0.0.1:4001/file/list?loc=D%3A%5Cproject%5Cdocs&ext=.md   ← پوشه
```

---

## خطاهای رایج — انجام نده

**مسیر**
- `loc=docs/perplexity-guid.md` → 400 (باید absolute باشد)
- از `integration_guide_file.relative_loc` مستقیم در API استفاده نکن → از `absolute_loc` یا `read_via`

**sync_data — method نامعتبر (همه 400)**
- `method=sync_finish`
- `method=finish`
- `method=commit_sync`
- `method=finalize_sync`

پایان sync = `method=add_chunk` + `finalize=true` (پارامتر جدا)

**file/edit streaming**
- فرستادن فقط `edit_id` بدون `loc` و `mode` → 400
- استفاده از `sync_data` برای ویرایش بخشی از فایل → فایل ناقص یا overwrite اشتباه

**aliasهای مجاز (اختیاری)**
- `path` به‌جای `loc`
- `/file/write` به‌جای `/file/sync_data`
- `content` به‌جای `payload` (فقط sync)
- `mode=overwrite` → `init_sync` ، `mode=append` → `add_chunk`

---

## محدودیت‌ها

- فقط GET (به‌جز `/run` POST برای cmd بلند)
- `loc` absolute ویندوز
- هر `payload` حداکثر ~1800 کاراکتر
- فقط از `127.0.0.1` در دسترس است
- PowerShell: `GET /run?cmd=...`

---

## این فایل

مسیر absolute این راهنما (نمونه):

```
D:\2 Curent project git\windows-api\docs\perplexity-guid.md
```

این فایل را به چت attach کن یا با `read_via` از `/help` بخوان.
