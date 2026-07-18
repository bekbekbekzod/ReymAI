import os
import random
import subprocess
import tempfile

from docxtpl import DocxTemplate
import qrcode

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DOCX = os.path.join(BASE_DIR, "certificate_template.docx")


def generate_4digit_code():
    """0000-9999 oralig'ida tasodifiy 4 xonali kod (string, boshida nollar bilan)."""
    return f"{random.randint(0, 9999):04d}"


def generate_qr_code(data_url: str, output_path: str):
    img = qrcode.make(data_url)
    img.save(output_path)


def generate_pdf_from_data(data: dict, cert_uuid: str, output_pdf_path: str):
    """
    1) certificate_template.docx ichidagi {{ placeholder }} larni docxtpl bilan to'ldiradi
    2) LibreOffice (soffice) headless rejimida docx -> pdf ga o'giradi
    """
    context = dict(data)
    context["cert_uuid"] = cert_uuid

    with tempfile.TemporaryDirectory() as tmp_dir:
        filled_docx_path = os.path.join(tmp_dir, f"{cert_uuid}.docx")

        doc = DocxTemplate(TEMPLATE_DOCX)
        doc.render(context)
        doc.save(filled_docx_path)

        # LibreOffice orqali PDF ga konvertatsiya
        result = subprocess.run(
            [
                "soffice", "--headless", "--norestore",
                "--convert-to", "pdf",
                "--outdir", tmp_dir,
                filled_docx_path,
            ],
            capture_output=True,
            timeout=60,
        )

        converted_pdf = os.path.join(tmp_dir, f"{cert_uuid}.pdf")
        if not os.path.exists(converted_pdf):
            raise RuntimeError(
                "LibreOffice PDF konvertatsiyasi muvaffaqiyatsiz: "
                + result.stderr.decode(errors="ignore")
            )

        os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
        os.replace(converted_pdf, output_pdf_path)
