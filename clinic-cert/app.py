import os
import uuid as uuid_lib
import random
import string
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, send_from_directory, flash, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from database import get_db, init_db
from cert_utils import (
    generate_pdf_from_data, generate_qr_code, generate_4digit_code
)
import storage_r2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GENERATED_DIR = os.path.join(BASE_DIR, "generated")
QR_DIR = os.path.join(BASE_DIR, "static", "qr")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-please-change")

os.makedirs(GENERATED_DIR, exist_ok=True)
os.makedirs(QR_DIR, exist_ok=True)

# Nechta marta noto'g'ri kod kiritilsa bloklanadi
MAX_ATTEMPTS = 5
LOCK_MINUTES = 15


# ---------------------------------------------------------------------------
# Yordamchi: admin sessiyasini tekshirish
# ---------------------------------------------------------------------------
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# ADMIN: Login / Logout
# ---------------------------------------------------------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        admin = db.execute(
            "SELECT * FROM admins WHERE username = ?", (username,)
        ).fetchone()
        if admin and check_password_hash(admin["password_hash"], password):
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            return redirect(url_for("admin_dashboard"))
        flash("Login yoki parol xato.", "error")
    return render_template("admin_login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


# ---------------------------------------------------------------------------
# ADMIN: Dashboard - barcha hujjatlar ro'yxati
# ---------------------------------------------------------------------------
@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    certs = db.execute(
        "SELECT * FROM certificates ORDER BY created_at DESC"
    ).fetchall()
    return render_template("admin_dashboard.html", certs=certs)


# ---------------------------------------------------------------------------
# ADMIN: Yangi ma'lumotnoma yaratish
# ---------------------------------------------------------------------------
@app.route("/admin/create", methods=["GET", "POST"])
@admin_required
def admin_create():
    if request.method == "POST":
        data = {
            "full_name": request.form.get("full_name", "").strip(),
            "birth_date": request.form.get("birth_date", "").strip(),
            "passport": request.form.get("passport", "").strip(),
            "address": request.form.get("address", "").strip(),
            "diagnosis": request.form.get("diagnosis", "").strip(),
            "purpose": request.form.get("purpose", "").strip(),
            "doctor_name": request.form.get("doctor_name", "").strip(),
            "clinic_name": request.form.get("clinic_name", "").strip(),
            "issue_date": request.form.get("issue_date") or datetime.now().strftime("%Y-%m-%d"),
            "valid_until": request.form.get("valid_until", "").strip(),
        }

        cert_uuid = str(uuid_lib.uuid4())
        code = generate_4digit_code()
        code_hash = generate_password_hash(code)

        db = get_db()
        db.execute(
            """INSERT INTO certificates
               (uuid, code_hash, full_name, birth_date, passport, address,
                diagnosis, purpose, doctor_name, clinic_name, issue_date,
                valid_until, created_at, created_by)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                cert_uuid, code_hash, data["full_name"], data["birth_date"],
                data["passport"], data["address"], data["diagnosis"],
                data["purpose"], data["doctor_name"], data["clinic_name"],
                data["issue_date"], data["valid_until"],
                datetime.utcnow().isoformat(), session.get("admin_username"),
            ),
        )
        db.commit()

        # PDF generatsiya qilish (docx shablon -> pdf)
        pdf_filename = f"{cert_uuid}.pdf"
        pdf_path = os.path.join(GENERATED_DIR, pdf_filename)
        generate_pdf_from_data(data, cert_uuid, pdf_path)

        # R2 sozlangan bo'lsa, PDF'ni doimiy saqlash uchun R2'ga yuklaymiz
        # va konteynerning vaqtinchalik diskidan o'chirib tashlaymiz
        # (Render free instansiyasi qayta ishga tushganda baribir yo'qoladi).
        if storage_r2.r2_enabled():
            storage_r2.upload_pdf(pdf_path, pdf_filename)
            os.remove(pdf_path)

        db.execute(
            "UPDATE certificates SET pdf_filename = ? WHERE uuid = ?",
            (pdf_filename, cert_uuid),
        )
        db.commit()

        # QR kod: tekshirish sahifasiga yo'naltiradi
        verify_url = url_for("verify_enter", cert_uuid=cert_uuid, _external=True)
        qr_filename = f"{cert_uuid}.png"
        generate_qr_code(verify_url, os.path.join(QR_DIR, qr_filename))

        return render_template(
            "admin_created.html",
            cert_uuid=cert_uuid,
            code=code,
            qr_filename=qr_filename,
            verify_url=verify_url,
        )

    return render_template("admin_create.html")


@app.route("/admin/cert/<cert_uuid>/pdf")
@admin_required
def admin_download_pdf(cert_uuid):
    db = get_db()
    cert = db.execute(
        "SELECT * FROM certificates WHERE uuid = ?", (cert_uuid,)
    ).fetchone()
    if not cert or not cert["pdf_filename"]:
        abort(404)
    if storage_r2.r2_enabled():
        url = storage_r2.get_presigned_url(cert["pdf_filename"], expires_seconds=300)
        return redirect(url)
    return send_from_directory(GENERATED_DIR, cert["pdf_filename"], as_attachment=True)


# ---------------------------------------------------------------------------
# PUBLIC: QR skanerlangandan keyin ochiladigan sahifa - 4 xonali kod so'raydi
# ---------------------------------------------------------------------------
@app.route("/verify/<cert_uuid>", methods=["GET", "POST"])
def verify_enter(cert_uuid):
    db = get_db()
    cert = db.execute(
        "SELECT * FROM certificates WHERE uuid = ?", (cert_uuid,)
    ).fetchone()

    if not cert:
        return render_template("verify_not_found.html"), 404

    # Bloklashni tekshirish
    attempts_row = db.execute(
        "SELECT * FROM verify_attempts WHERE uuid = ?", (cert_uuid,)
    ).fetchone()

    locked_until = None
    if attempts_row and attempts_row["locked_until"]:
        locked_until = datetime.fromisoformat(attempts_row["locked_until"])
        if locked_until > datetime.utcnow():
            return render_template(
                "verify_locked.html", locked_until=locked_until
            )

    if request.method == "POST":
        entered_code = request.form.get("code", "").strip()

        if check_password_hash(cert["code_hash"], entered_code):
            # muvaffaqiyatli - urinishlarni tozalash
            db.execute("DELETE FROM verify_attempts WHERE uuid = ?", (cert_uuid,))
            db.commit()
            return redirect(url_for("verify_result", cert_uuid=cert_uuid))
        else:
            fail_count = (attempts_row["fail_count"] + 1) if attempts_row else 1
            lock_until_value = None
            if fail_count >= MAX_ATTEMPTS:
                lock_until_value = (
                    datetime.utcnow() + timedelta(minutes=LOCK_MINUTES)
                ).isoformat()

            if attempts_row:
                db.execute(
                    "UPDATE verify_attempts SET fail_count = ?, locked_until = ? WHERE uuid = ?",
                    (fail_count, lock_until_value, cert_uuid),
                )
            else:
                db.execute(
                    "INSERT INTO verify_attempts (uuid, fail_count, locked_until) VALUES (?,?,?)",
                    (cert_uuid, fail_count, lock_until_value),
                )
            db.commit()

            if lock_until_value:
                return render_template(
                    "verify_locked.html",
                    locked_until=datetime.fromisoformat(lock_until_value),
                )
            flash(f"Kod noto'g'ri. Qolgan urinishlar: {MAX_ATTEMPTS - fail_count}", "error")

    return render_template("verify_enter.html", cert_uuid=cert_uuid)


@app.route("/verify/<cert_uuid>/result")
def verify_result(cert_uuid):
    db = get_db()
    cert = db.execute(
        "SELECT * FROM certificates WHERE uuid = ?", (cert_uuid,)
    ).fetchone()
    if not cert:
        abort(404)
    return render_template("verify_result.html", cert=cert)


@app.route("/verify/<cert_uuid>/download")
def verify_download(cert_uuid):
    # Diqqat: bu route faqat verify_result orqali ma'lum bo'lgan uuid uchun ishlaydi.
    # Qo'shimcha himoya uchun productionda bu yerga ham bir martalik token qo'shish tavsiya etiladi.
    db = get_db()
    cert = db.execute(
        "SELECT * FROM certificates WHERE uuid = ?", (cert_uuid,)
    ).fetchone()
    if not cert or not cert["pdf_filename"]:
        abort(404)
    if storage_r2.r2_enabled():
        url = storage_r2.get_presigned_url(cert["pdf_filename"], expires_seconds=300)
        return redirect(url)
    return send_from_directory(GENERATED_DIR, cert["pdf_filename"], as_attachment=False)


@app.route("/")
def index():
    return redirect(url_for("admin_login"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
