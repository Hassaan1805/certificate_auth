from flask import Flask, request, render_template, jsonify, send_file
import hashlib
import os
from datetime import datetime
import pytesseract
from PIL import Image
import mysql.connector
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import requests
import cv2
import numpy as np
import fitz  # PyMuPDF
from PyPDF2 import PdfReader  # Add this import

app = Flask(__name__)

OUTPUT_DIR = "certificates"
os.makedirs(OUTPUT_DIR, exist_ok=True)

db_config = {
    'user': 'root',
    'password': 'tiger',
    'host': 'localhost',
    'database': 'certificate_auth'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/')
def index():
    return render_template("index.html")

def generate_certificate(name, organization, issue_date, expiry_date, completion_date, issuer, serial_number):
    try:
        certificate_text = f"""
        CERTIFICATE OF ACHIEVEMENT
        This is to certify that
        Name: {name}
        Organization: {organization}
        Has successfully completed the requirements
        of the program and is awarded this certificate.
        Issue Date: {issue_date}
        Expiry Date: {expiry_date}
        Completion Date: {completion_date}
        Issuer: {issuer}
        Serial Number: {serial_number}
        Certificate Issued On: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """

        cert_data = f"{name}|{organization}|{issue_date}|{expiry_date}|{completion_date}|{issuer}|{serial_number}"
        cert_hash = hashlib.sha256(cert_data.encode()).hexdigest()

        certificate_text += f"Certificate Hash: {cert_hash[:20]}...\n"  # to shorten the hash value

        cert_filename = f"certificate_{serial_number}.pdf"
        cert_filepath = os.path.join(OUTPUT_DIR, cert_filename)
        c = canvas.Canvas(cert_filepath, pagesize=letter)
        width, height = letter

        c.setFont("Helvetica-Bold", 24)
        c.drawString(100, height - 100, "CERTIFICATE OF ACHIEVEMENT")
        c.setFont("Helvetica", 18)
        c.drawString(100, height - 150, f"This is to certify that")
        c.setFont("Helvetica-Bold", 20)
        c.drawString(100, height - 200, f"Name: {name}")
        c.setFont("Helvetica", 18)
        c.drawString(100, height - 250, f"Organization: {organization}")
        c.drawString(100, height - 300, f"Has successfully completed the requirements")
        c.drawString(100, height - 350, f"of the program and is awarded this certificate.")
        c.drawString(100, height - 400, f"Issue Date: {issue_date}")
        c.drawString(100, height - 450, f"Expiry Date: {expiry_date}")
        c.drawString(100, height - 500, f"Completion Date: {completion_date}")
        c.drawString(100, height - 550, f"Issuer: {issuer}")
        c.drawString(100, height - 600, f"Serial Number: {serial_number}")
        c.drawString(100, height - 650, f"Certificate Issued On: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        c.drawString(100, height - 700, f"Certificate Hash: {cert_hash[:20]}...")

        c.save()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO certificates (serial_number, name, organization, issue_date, expiry_date, completion_date, issuer, hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (serial_number, name, organization, issue_date, expiry_date, completion_date, issuer, cert_hash))
        conn.commit()
        cursor.close()
        conn.close()
        return cert_filename
    except Exception as e:
        print(f"Error generating certificate: {e}")
        return None

@app.route('/generate', methods=['POST'])
def generate():
    name = request.form.get("name")
    organization = request.form.get("organization")
    issue_date = request.form.get("issue_date")
    expiry_date = request.form.get("expiry_date")
    completion_date = request.form.get("completion_date")
    issuer = request.form.get("issuer")
    serial_number = request.form.get("serial_number")
    if not all([name, organization, issue_date, expiry_date, completion_date, issuer, serial_number]):
        return jsonify({"error": "All fields are required"}), 400
    cert_filename = generate_certificate(name, organization, issue_date, expiry_date, completion_date, issuer, serial_number)
    if not cert_filename:
        return jsonify({"error": "Failed to generate certificate"}), 500
    return jsonify({"success": True, "file_path": cert_filename})

@app.route('/authenticate', methods=['POST'])
def authenticate():
    serial_number = request.form.get("serial_number")
    if not serial_number:
        return jsonify({"error": "Serial number is required"}), 400
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM certificates WHERE serial_number = %s", (serial_number,))
    metadata = cursor.fetchone()
    cursor.fetchall()
    cursor.close()
    conn.close()
    if not metadata:
        return jsonify({"error": "Certificate not found"}), 404
    stored_hash = metadata.get("hash")
    if stored_hash:
        return jsonify({"message": "Certificate is authentic"}), 200
    else:
        return jsonify({"error": "Certificate is not authentic"}), 400

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    file_path = os.path.join(OUTPUT_DIR, file.filename)
    file.save(file_path)
    extracted_text = ""
    try:
        if file.content_type == "application/pdf":
            reader = PdfReader(file_path)
            for page in reader.pages:
                extracted_text += page.extract_text()
        elif file.content_type.startswith("image/"):
            image = Image.open(file_path)
            extracted_text = pytesseract.image_to_string(image)
    except Exception as e:
        return jsonify({"error": f"Failed to extract text: {str(e)}"}), 500

    serial_number = None
    name = None
    organization = None
    issue_date = None
    expiry_date = None
    completion_date = None
    issuer = None

    for line in extracted_text.split("\n"):
        if "Serial Number:" in line:
            serial_number = line.split("Serial Number:")[1].strip()
        if "Name:" in line:
            name = line.split("Name:")[1].strip()
        if "Organization:" in line:
            organization = line.split("Organization:")[1].strip()
        if "Issue Date:" in line:
            issue_date = line.split("Issue Date:")[1].strip()
        if "Expiry Date:" in line:
            expiry_date = line.split("Expiry Date:")[1].strip()
        if "Completion Date:" in line:
            completion_date = line.split("Completion Date:")[1].strip()
        if "Issuer:" in line:
            issuer = line.split("Issuer:")[1].strip()

    if not serial_number:
        return jsonify({"error": "Could not extract serial number from the uploaded file"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM certificates WHERE serial_number = %s", (serial_number,))
    metadata = cursor.fetchone()
    cursor.fetchall()
    cursor.close()
    conn.close()
    if metadata:
        return jsonify({
            "message": "Certificate is authentic",
            "details": {
                "name": metadata["name"],
                "organization": metadata["organization"],
                "issue_date": metadata["issue_date"],
                "expiry_date": metadata["expiry_date"],
                "completion_date": metadata["completion_date"],
                "issuer": metadata["issuer"],
                "serial_number": metadata["serial_number"]
            }
        }), 200

    return jsonify({"error": "Certificate is not authentic"}), 400

@app.route('/upload_udemy', methods=['POST'])
def upload_udemy():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    file_path = os.path.join(OUTPUT_DIR, file.filename)
    file.save(file_path)
    extracted_text = ""
    try:
        if file.content_type == "application/pdf":
            reader = PdfReader(file_path)
            for page in reader.pages:
                extracted_text += page.extract_text()
        elif file.content_type.startswith("image/"):
            image = Image.open(file_path)
            extracted_text = pytesseract.image_to_string(image)
    except Exception as e:
        return jsonify({"error": f"Failed to extract text: {str(e)}"}), 500

    certificate_url = None
    for line in extracted_text.split("\n"):
        if "ude.my" in line:
            # Clean the URL by removing any extra text and spaces
            certificate_url = line.strip().replace("Certificate url:", "").strip()
            break

    if not certificate_url:
        return jsonify({"error": "Cant detect a legit Udemy URL , This certiifcate might be fraud"}), 400

    # Ensure the URL is properly formatted
    if not certificate_url.startswith("http"):
        certificate_url = "https://" + certificate_url

    try:
        response = requests.get(certificate_url)
        if response.status_code == 200:
            return jsonify({"message": "Udemy certificate is valid", "certificate_url": certificate_url}), 200
        else:
            return jsonify({"error": "Udemy certificate URL is not valid"}), 400
    except requests.RequestException as e:
        return jsonify({"error": f"Failed to verify Udemy certificate URL: {str(e)}"}), 500

@app.route('/upload_great_learning', methods=['POST'])
def upload_great_learning():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    file_path = os.path.join(OUTPUT_DIR, file.filename)
    file.save(file_path)
    extracted_text = ""
    try:
        if file.content_type == "application/pdf":
            reader = PdfReader(file_path)
            for page in reader.pages:
                extracted_text += page.extract_text()
        elif file.content_type.startswith("image/"):
            image = Image.open(file_path)
            extracted_text = pytesseract.image_to_string(image)
    except Exception as e:
        return jsonify({"error": f"Failed to extract text: {str(e)}"}), 500

    certificate_url = None
    for line in extracted_text.split("\n"):
        if "greatlearning" in line:
            # Clean the URL by removing any extra text and spaces
            certificate_url = line.strip().replace("Certificate url:", "").strip()
            break

    if not certificate_url:
        return jsonify({"error": "Cant detect a legit Great Learning URL , This certiifcate might be fraud"}), 400

    # Ensure the URL is properly formatted
    if not certificate_url.startswith("http"):
        certificate_url = "https://" + certificate_url

    try:
        response = requests.get(certificate_url)
        if response.status_code == 200:
            return jsonify({"message": "Great Learning certificate is valid", "certificate_url": certificate_url}), 200
        else:
            return jsonify({"error": "Great Learning certificate URL is not valid"}), 400
    except requests.RequestException as e:
        return jsonify({"error": f"Failed to verify Great Learning certificate URL: {str(e)}"}), 500

@app.route('/upload_google_education', methods=['POST'])
def upload_google_education():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    file_path = os.path.join(OUTPUT_DIR, file.filename)
    file.save(file_path)

    try:
        if file.content_type == "application/pdf":
            doc = fitz.open(file_path)
            for page in doc:
                page_image = convert_pdf_page_to_image(page)
                qr_code_url = extract_qr_code(page_image)
                if qr_code_url:
                    break
        elif file.content_type.startswith("image/"):
            image = Image.open(file_path)
            qr_code_url = extract_qr_code(image)
    except Exception as e:
        return jsonify({"error": f"Failed to extract QR code: {str(e)}"}), 500

    if not qr_code_url:
        return jsonify({"error": "Cannot detect a valid Google QR code in the uploaded file, This might be a fraud"}), 400

    if "skillshop.credential.net" in qr_code_url:
        return jsonify({"message": "Google Education certificate is valid", "certificate_url": qr_code_url}), 200
    else:
        return jsonify({"error": "Google Education certificate URL is not valid"}), 400

def convert_pdf_page_to_image(page):
    # Convert PDF page to image using PyMuPDF
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img

def extract_qr_code(image):
    try:
        image_np = np.array(image)
        gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
        qr_detector = cv2.QRCodeDetector()
        data, _, _ = qr_detector.detectAndDecode(gray)
        return data
    except Exception as e:
        print(f"Error extracting QR code: {e}")
        return None

@app.route('/download')
def download():
    file_name = request.args.get('file')
    if not file_name:
        return jsonify({"error": "File name is required"}), 400
    file_path = os.path.join(OUTPUT_DIR, file_name)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({"error": "File not found"}), 404

@app.route('/delete', methods=['POST'])
def delete_file():
    file_name = request.form.get("file_name")
    if not file_name:
        return jsonify({"error": "File name is required"}), 400
    file_path = os.path.join(OUTPUT_DIR, file_name)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"message": f"File '{file_name}' deleted successfully"}), 200
    else:
        return jsonify({"error": "File not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)