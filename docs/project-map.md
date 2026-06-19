
# نقشه فایل‌های پروژه – windows-cmd-api

---

## ساختار پوشه‌بندی

```
windows-cmd-api/
│
├── app.py                  ← نقطه ورود اصلی؛ سرویس رو راه‌اندازی می‌کنه
│
├── .env                    ← متغیرهای محیطی (پورت، مسیرها، تنظیمات)
├── .env.example            ← نمونه .env برای اولین راه‌اندازی
├── requirements.txt        ← لیست وابستگی‌های Python
│
├── config.py               ← خواندن و مدیریت متغیرهای محیطی
│
├── core/
│   ├── __init__.py
│   ├── runner.py           ← اجرای دستورات در PowerShell و برگرداندن خروجی
│   ├── blocklist.py        ← بارگذاری و بررسی لیست دستورات خطرناک
│   ├── token_store.py      ← ساخت، نگهداری و انقضای توکن‌های تأیید
│   └── server_lifecycle.py ← آزاد کردن پورت و توقف پروسه قبلی هنگام شروع/خروج
│
├── routes/
│   ├── __init__.py
│   ├── run.py              ← اندپوینت POST /run
│   ├── confirm.py          ← اندپوینت GET و POST /confirm/{token}
│   ├── blocklist_route.py  ← اندپوینت GET /blocklist
│   └── help.py             ← اندپوینت GET /help
│
├── templates/
│   └── confirm.html        ← صفحه تأیید دستور خطرناک (مرورگر)
│
└── data/
    ├── blocklist.txt       ← لیست کلمات کلیدی دستورات نیازمند تأیید
    └── server.pid          ← PID سرور در حال اجرا (خودکار؛ موقت)
```

---

## توضیح هر فایل

### فایل‌های ریشه

| فایل | مسئولیت |
|------|---------|
| `app.py` | ساخت اپلیکیشن Flask، رجیستر routes، redirect از `/` به `/help`، مدیریت چرخه سرور |
| `.env` | مقادیر واقعی متغیرهای محیطی — **نباید** توی Git باشه |
| `.env.example` | نمونه خالی `.env` برای راهنمایی — توی Git باشه |
| `requirements.txt` | وابستگی‌ها: Flask، python-dotenv |
| `config.py` | یه‌بار `.env` رو می‌خونه و مقادیر رو در دسترس بقیه فایل‌ها می‌ذاره |

---

### پوشه `core/` — منطق اصلی

| فایل | مسئولیت |
|------|---------|
| `runner.py` | دستور رو می‌گیره، توی PowerShell اجرا می‌کنه، خروجی و خطا رو برمی‌گردونه؛ timeout رو مدیریت می‌کنه |
| `blocklist.py` | فایل `blocklist.txt` رو می‌خونه؛ تابعی که چک می‌کنه دستور ورودی با یکی از قوانین تطابق داره یا نه |
| `token_store.py` | توکن یک‌بار مصرف می‌سازه؛ دستور رو بهش وصل می‌کنه؛ بعد از تأیید/رد یا انقضا حذفش می‌کنه |
| `server_lifecycle.py` | پروسه قبلی و اشغال‌کننده پورت رو می‌بنده؛ PID رو ذخیره و هنگام خروج پاک می‌کنه |

---

### پوشه `routes/` — اندپوینت‌ها

| فایل | اندپوینت | متد | کار |
|------|---------|-----|-----|
| `run.py` | `/run` | GET, POST | دستور می‌گیره (GET: query `cmd` / POST: JSON)؛ اگه مجازه اجرا می‌کنه؛ اگه خطرناکه توکن می‌سازه |
| `confirm.py` | `/confirm/<token>` | GET | صفحه HTML تأیید رو نشون می‌ده |
| `confirm.py` | `/confirm/<token>` | POST | تأیید یا رد کاربر رو دریافت و پردازش می‌کنه |
| `blocklist_route.py` | `/blocklist` | GET | محتوای فعلی blocklist رو برمی‌گردونه |
| `help.py` | `/help` | GET | راهنمای API + بخش `for_ai_assistants` برای دستیارهای هوش مصنوعی |

---

### پوشه `templates/`

| فایل | مسئولیت |
|------|---------|
| `confirm.html` | صفحه ساده مرورگری؛ دستور رو نشون می‌ده؛ دو دکمه تأیید و رد داره؛ نتیجه اجرا رو بعد از تأیید نمایش می‌ده |

---

### پوشه `data/`

| فایل | مسئولیت |
|------|---------|
| `blocklist.txt` | هر خط یه کلمه کلیدی؛ اگه دستور ورودی شامل اون بشه، نیاز به تأیید داره |
| `server.pid` | شناسه پروسه سرور فعلی — هنگام شروع/خروج خودکار مدیریت می‌شه |

---

## ترتیب پیاده‌سازی پیشنهادی

```
1. requirements.txt + .env.example
2. config.py
3. core/blocklist.py
4. core/token_store.py
5. core/runner.py
6. core/server_lifecycle.py
7. routes/help.py
8. routes/run.py
9. routes/confirm.py
10. routes/blocklist_route.py
11. templates/confirm.html
12. app.py
```

> هر مرحله روی پایه مرحله قبل بنا می‌شه. با این ترتیب می‌شه هر فایل رو جداگانه تست کرد.

---

## وابستگی‌های بین فایل‌ها

```
app.py
 ├── config.py
 ├── core/server_lifecycle.py
 └── routes/
      ├── run.py
      │    ├── core/blocklist.py
      │    ├── core/token_store.py
      │    └── core/runner.py
      ├── confirm.py
      │    ├── core/token_store.py
      │    ├── core/runner.py
      │    └── templates/confirm.html
      ├── blocklist_route.py
      │    └── core/blocklist.py
      └── help.py
```

