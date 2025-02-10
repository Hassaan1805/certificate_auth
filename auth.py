from flask import Flask, request, render_template, jsonify, send_file
import hashlib
import os
from datetime import datetime
from PyPDF2 import PdfReader  # For extracting text from PDFs
import pytesseract  # For OCR (Optical Character Recognition)
from PIL import Image  # For handling images
import mysql.connector
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)

# Configuration
OUTPUT_DIR = "certificates"  # Folder to store generated certificates
os.makedirs(OUTPUT_DIR, exist_ok=True)

# MySQL Database Configuration
db_config = {
    'user': 'root',
    'password':'tiger',
    'host': 'localhost',
    'database': 'certificate_auth'
}

# Function to connect to the database
def get_db_connection():
    return mysql.connector.connect(**db_config)

@app.route('/')
def index():
    return render_template("index.html")

def generate_certificate(name, organization, issue_date, expiry_date, completion_date, issuer, serial_number):
    try:
        # Certificate Text Template
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
        # Generate SHA-256 hash for verification
        cert_data = f"{name}|{organization}|{issue_date}|{expiry_date}|{completion_date}|{issuer}|{serial_number}"
        cert_hash = hashlib.sha256(cert_data.encode()).hexdigest()
        # Add hash to certificate text
        certificate_text += f"Certificate Hash: {cert_hash[:20]}...\n"  # Shortened hash

        # Create a PDF file
        cert_filename = f"certificate_{serial_number}.pdf"
        cert_filepath = os.path.join(OUTPUT_DIR, cert_filename)
        c = canvas.Canvas(cert_filepath, pagesize=letter)
        width, height = letter

        # Add content to the PDF
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

        # Save the PDF file
        c.save()

        # Store metadata in the database
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
    # Extract form data
    name = request.form.get("name")
    organization = request.form.get("organization")
    issue_date = request.form.get("issue_date")
    expiry_date = request.form.get("expiry_date")
    completion_date = request.form.get("completion_date")
    issuer = request.form.get("issuer")
    serial_number = request.form.get("serial_number")
    # Validate input
    if not all([name, organization, issue_date, expiry_date, completion_date, issuer, serial_number]):
        return jsonify({"error": "All fields are required"}), 400
    # Generate the certificate
    cert_filename = generate_certificate(name, organization, issue_date, expiry_date, completion_date, issuer, serial_number)
    if not cert_filename:
        return jsonify({"error": "Failed to generate certificate"}), 500
    return jsonify({"success": True, "file_path": cert_filename})

@app.route('/authenticate', methods=['POST'])
def authenticate():
    # Extract serial number from form data
    serial_number = request.form.get("serial_number")
    if not serial_number:
        return jsonify({"error": "Serial number is required"}), 400
    # Retrieve metadata for the given serial number from the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM certificates WHERE serial_number = %s", (serial_number,))
    metadata = cursor.fetchone()
    cursor.fetchall()  # Fetch all remaining results to avoid unread result error
    cursor.close()
    conn.close()
    if not metadata:
        return jsonify({"error": "Certificate not found"}), 404
    # Verify the stored hash
    stored_hash = metadata.get("hash")
    if stored_hash:
        return jsonify({"message": "Certificate is authentic"}), 200
    else:
        return jsonify({"error": "Certificate is not authentic"}), 400

@app.route('/upload', methods=['POST'])
def upload():
    # Check if a file was uploaded
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Save the uploaded file temporarily
    file_path = os.path.join(OUTPUT_DIR, file.filename)
    file.save(file_path)

    # Extract text from the uploaded file
    extracted_text = ""
    try:
        if file.content_type == "application/pdf":
            # Extract text from PDF
            reader = PdfReader(file_path)
            for page in reader.pages:
                extracted_text += page.extract_text()
        elif file.content_type.startswith("image/"):
            # Extract text from image using OCR
            image = Image.open(file_path)
            extracted_text = pytesseract.image_to_string(image)
    except Exception as e:
        return jsonify({"error": f"Failed to extract text: {str(e)}"}), 500

    # Parse the extracted text to find key fields
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

    # Validate the extracted metadata
    if not serial_number:
        return jsonify({"error": "Could not extract serial number from the uploaded file"}), 400

    # Check if the extracted metadata matches any stored certificate in the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM certificates WHERE serial_number = %s", (serial_number,))
    metadata = cursor.fetchone()
    cursor.fetchall()  # Fetch all remaining results to avoid unread result error
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

@app.route('/download')
def download():
    # Get the file name from query parameters
    file_name = request.args.get('file')
    if not file_name:
        return jsonify({"error": "File name is required"}), 400
    # Construct the full file path
    file_path = os.path.join(OUTPUT_DIR, file_name)
    # Check if the file exists
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({"error": "File not found"}), 404

@app.route('/delete', methods=['POST'])
def delete_file():
    # Extract the file name from the request (if needed)
    file_name = request.form.get("file_name")
    if not file_name:
        return jsonify({"error": "File name is required"}), 400
    # Construct the full file path
    file_path = os.path.join(OUTPUT_DIR, file_name)
    # Check if the file exists and delete it
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"message": f"File '{file_name}' deleted successfully"}), 200
    else:
        return jsonify({"error": "File not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)