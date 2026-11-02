# FreeAmir — بازنویسی با Django + PWA

بازنویسی کامل پروژه‌ی [FreeAmir](https://github.com/Jooyeshgar/FreeAmir) با پایتون/Django — همراه با PWA و رابط کاربری ریسپانسیو.

## وضعیت

| بخش | وضعیت |
|---|---|
| اسکلت پروژه | ✅ |
| احراز هویت / نقش‌ها | ✅ |
| هسته حسابداری دوبل | ✅ |
| تراز آزمایشی / دفتر کل | ✅ |
| ترازنامه / صورت سود و زیان | ✅ |
| فروش + COGS خودکار | ✅ |
| برگشت از فروش | ✅ |
| خرید + تأمین‌کننده | ✅ |
| برگشت از خرید (با واریانس) | ✅ |
| انبار + بهای میانگین موزون | ✅ |
| مودیان — ۴ نوع سند + ۷ endpoint | ✅ |
| لاگ فعالیت | ✅ |
| منابع انسانی + حقوق و مالیات پله‌ای | ✅ |
| فرآیند تأیید اسناد | ✅ |
| بستن سال مالی (انتقال به سود انباشته) | ✅ |
| PWA — نصب، آفلاین، manifest | ✅ |
| رابط کاربری موبایل | ✅ |

## نصب

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # SECRET_KEY را عوض کنید
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py init_coa --company-id 1
python manage.py seed_tax_brackets --year 1403
python manage.py runserver
```

> **migration:** `makemigrations` را بدون نام اپ اجرا کنید تا همه‌ی اپ‌ها با هم migrate شوند.

## ساختار

```
config/                 تنظیمات Django
apps/
  core/                 Company، FiscalYear، Approval، Activity، PWA views
  accounts/             کاربر سفارشی، نقش‌ها
  accounting/           Account، Journal، reports، closing
  sales/                Customer، Product، Invoice، Return، COGS
  purchases/            Supplier، PurchaseInvoice، Return
  inventory/            Warehouse، StockMove، WAC
  hr/                   Employee، Attendance، Payroll، TaxBracket
  moadian/              امضا + ارسال + استعلام
  api/                  REST API
templates/              همه‌ی templateها
static/                 manifest، service-worker، pwa.js، icons
```

## تست

```
python manage.py test apps.accounting apps.inventory apps.sales apps.purchases apps.moadian apps.hr
```

## PWA

### نصب

- **Chrome/Edge (Android):** منو → Add to Home screen
- **Safari (iOS):** Share → Add to Home Screen (نیاز به PNG دارد — ادامه ببینید)

### تبدیل SVG به PNG برای iOS

```
rsvg-convert -w 192 -h 192 static/icons/icon-192.svg > static/icons/icon-192.png
rsvg-convert -w 512 -h 512 static/icons/icon-512.svg > static/icons/icon-512.png
rsvg-convert -w 180 -h 180 static/icons/icon-192.svg > static/icons/apple-touch-icon.png
```

سپس در `templates/base.html` و `static/manifest.json` مسیرها را به PNG تغییر دهید.

### نکات

- `service-worker.js` از **ریشه** (`/service-worker.js`) سرو می‌شود
- در `DEBUG=True`، SW ثبت نمی‌شود
- SW فقط روی **HTTPS** (یا localhost) اجرا می‌شود
- پاک کردن SW قدیمی: DevTools → Application → Service Workers → Unregister

## مجوز

GPL-3 — سازگار با پروژه‌ی اصلی.

