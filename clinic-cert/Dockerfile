FROM python:3.11-slim

# LibreOffice - docx -> pdf konvertatsiyasi uchun kerak
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/instance /app/generated /app/static/qr

ENV PORT=10000
EXPOSE 10000

# Render "Disk" ulangan bo'lsa, /app/instance va /app/generated papkalarini
# doimiy diskka ulash tavsiya etiladi (pastdagi README ga qarang)

CMD python3 database.py && gunicorn -w 2 -b 0.0.0.0:${PORT} --timeout 120 app:app
