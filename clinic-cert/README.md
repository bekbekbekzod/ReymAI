# Klinika ma'lumotnoma tizimi (docx → PDF + QR tekshiruv)

## Qanday ishlaydi

1. **Admin** (`/admin/login`) tizimga kiradi va `/admin/create` orqali yangi
   ma'lumotnoma yaratadi (bemor ma'lumotlarini kiritadi).
2. Server `certificate_template.docx` shablonini bemor ma'lumotlari bilan
   to'ldiradi (docxtpl), so'ng LibreOffice yordamida PDF ga aylantiradi.
3. Har bir hujjat uchun: **UUID**, **4 xonali tekshiruv kodi** va shu UUID'ga
   yo'naltiruvchi **QR kod** generatsiya qilinadi. Kod faqat bir marta
   ko'rsatiladi (bazada faqat hash saqlanadi) — shuning uchun uni chop etilgan
   hujjatga darhol yozib qo'yish kerak.
4. PDF fayl serverda (`/generated` papkasida) saqlanadi va istalgan vaqt
   (5-6 oydan keyin ham) qayta ochilishi mumkin.
5. **Oddiy foydalanuvchi** QR kodni skanerlaydi → `/verify/<uuid>` sahifasiga
   tushadi → 4 xonali kodni kiritadi → hujjat ma'lumotlari va yuklab olish
   havolasini ko'radi.
6. Noto'g'ri kod 5 marta ketma-ket kiritilsa, shu hujjat uchun 15 daqiqaga
   bloklanadi (bruteforce'dan himoya, chunki 4 xonali kod atigi 10 000
   variant).

## Muhim: brendlash

Bu tizim **klinikangizning o'z nomi/domeni** ostida ishlatilishi kerak.
`certificate_template.docx` faylini o'z logotipingiz, klinika nomi, MUHR
matni va rasmiy rekvizitlar bilan tahrirlang (Word'da oching, matnni
o'zgartiring, `{{ }}` ichidagi joylarni tegmasdan qoldiring).

## Local ishga tushirish

```bash
# LibreOffice o'rnatilgan bo'lishi kerak (docx -> pdf uchun)
# Ubuntu/Debian: sudo apt install libreoffice

pip install -r requirements.txt
python3 database.py            # bazani yaratadi
python3 create_admin.py admin sizning_parolingiz   # birinchi admin
python3 app.py                 # http://localhost:5000
```

## Render.com ga joylash

1. Reponi Render'ga ulang, **"Docker"** muhitini tanlang (Dockerfile avtomatik
   topiladi).
2. **Persistent Disk** qo'shing (Render dashboard → Disks), masalan 1GB,
   mount path: `/app/instance` va yana bittasi `/app/generated` uchun
   (yoki ikkalasini bitta disk ichida papka sifatida saqlang, chunki
   Render bepul rejada bitta disk beradi — shu holda Dockerfile'dagi
   papkalarni disk ichiga ko'chiring).
3. Environment Variables bo'limida qo'shing:
   - `SECRET_KEY` = uzun tasodifiy satr
4. Deploy bo'lgandan keyin, Render "Shell" orqali birinchi adminni yarating:
   ```bash
   python3 create_admin.py admin sizning_parolingiz
   ```
5. `/admin/login` orqali kiring.

## Diqqat: PDF saqlash haqida

Render'ning bepul (free) instansiyalari **disk persistent emas** — konteyner
qayta ishga tushganda fayllar yo'qoladi. 5-6 oydan keyin ham hujjatni
ochish kerak bo'lsa, albatta:
- Render **Persistent Disk** (pullik reja) ulang, YOKI
- PDF fayllarni tashqi saqlash xizmatiga (masalan S3-compatible storage,
  Cloudflare R2, yoki shunga o'xshash) yuklashga o'tkazing.

Agar xohlasangiz, keyingi qadam sifatida S3/R2 integratsiyasini ham
qo'shib beraman — shunda fayllar konteynerdan mustaqil, doimiy saqlanadi.

## Fayl tuzilishi

```
clinic-cert/
├── app.py                     # Flask route'lar
├── database.py                # SQLite sxema
├── cert_utils.py               # PDF/QR/kod generatsiya
├── create_admin.py             # Admin yaratish CLI
├── certificate_template.docx   # Word shablon (o'zingiz tahrirlaysiz)
├── requirements.txt
├── Dockerfile
├── templates/                  # HTML sahifalar
└── static/                     # CSS + QR rasmlar
```
