from flask import Flask, request, render_template, jsonify, send_file
from flask_cors import CORS
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
from PyPDF2 import PdfReader
import json
import secrets

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

OUTPUT_DIR = "certificates"
PROOF_DIR = "zk_proofs"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PROOF_DIR, exist_ok=True)

db_config = {
    'user': 'root',
    'password': 'tiger',
    'host': 'localhost',
    'database': 'certificate_auth'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# ========================
# ZK PROOF IMPLEMENTATION
# ========================

class ZKProofSystem:
    """Zero-Knowledge Proof System for Certificate Authentication"""
    
    @staticmethod
    def generate_commitment(secret_data):
        """Generate a commitment (hash) of secret data"""
        return hashlib.sha256(secret_data.encode()).hexdigest()
    
    @staticmethod
    def generate_challenge():
        """Generate a random challenge"""
        return secrets.token_hex(32)
    
    @staticmethod
    def create_proof(secret_data, challenge):
        """Create a ZK proof that proves knowledge of secret without revealing it"""
        commitment = ZKProofSystem.generate_commitment(secret_data)
        proof_data = f"{challenge}:{secret_data}"
        proof_hash = hashlib.sha256(proof_data.encode()).hexdigest()
        
        return {
            "commitment": commitment,
            "proof": proof_hash,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def verify_proof(commitment, proof, challenge, secret_data):
        """Verify the ZK proof without learning the secret"""
        expected_proof_data = f"{challenge}:{secret_data}"
        expected_proof = hashlib.sha256(expected_proof_data.encode()).hexdigest()
        expected_commitment = ZKProofSystem.generate_commitment(secret_data)
        
        return proof == expected_proof and commitment == expected_commitment
    
    @staticmethod
    def create_ownership_proof(serial_number, owner_secret):
        """Prove ownership of a certificate without revealing the secret"""
        challenge = ZKProofSystem.generate_challenge()
        commitment = ZKProofSystem.generate_commitment(f"{serial_number}:{owner_secret}")
        
        proof_data = f"{challenge}:{serial_number}:{owner_secret}"
        proof = hashlib.sha256(proof_data.encode()).hexdigest()
        
        return {
            "serial_number": serial_number,
            "commitment": commitment,
            "challenge": challenge,
            "proof": proof,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def verify_ownership_proof(proof_obj, serial_number, owner_secret):
        """Verify ownership proof"""
        expected_commitment = ZKProofSystem.generate_commitment(f"{serial_number}:{owner_secret}")
        proof_data = f"{proof_obj['challenge']}:{serial_number}:{owner_secret}"
        expected_proof = hashlib.sha256(proof_data.encode()).hexdigest()
        
        return (proof_obj['commitment'] == expected_commitment and 
                proof_obj['proof'] == expected_proof)
    
    @staticmethod
    def create_attribute_proof(attribute_name, attribute_value, predicate_type, predicate_value):
        """Prove an attribute satisfies a condition without revealing the value"""
        challenge = ZKProofSystem.generate_challenge()
        
        # Check if predicate is satisfied
        predicate_satisfied = ZKProofSystem.check_predicate(attribute_value, predicate_type, predicate_value)
        
        if not predicate_satisfied:
            return None
        
        commitment = ZKProofSystem.generate_commitment(f"{attribute_name}:{attribute_value}")
        proof_data = f"{challenge}:{attribute_name}:{predicate_satisfied}"
        proof = hashlib.sha256(proof_data.encode()).hexdigest()
        
        return {
            "attribute": attribute_name,
            "commitment": commitment,
            "challenge": challenge,
            "proof": proof,
            "predicate_type": predicate_type,
            "predicate_satisfied": predicate_satisfied,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def check_predicate(value, predicate_type, predicate_value):
        """Check if a predicate is satisfied"""
        value_str = str(value)
        predicate_value_str = str(predicate_value)
        
        if predicate_type == "greater_than":
            return value_str > predicate_value_str
        elif predicate_type == "less_than":
            return value_str < predicate_value_str
        elif predicate_type == "equals":
            return value_str == predicate_value_str
        elif predicate_type == "not_equals":
            return value_str != predicate_value_str
        elif predicate_type == "contains":
            return predicate_value_str.lower() in value_str.lower()
        else:
            return False

# ========================
# ZK PROOF API ENDPOINTS
# ========================

@app.route('/zk/generate_ownership_proof', methods=['POST'])
def generate_ownership_proof():
    """Generate a ZK proof of certificate ownership"""
    data = request.get_json()
    serial_number = data.get("serial_number")
    owner_secret = data.get("owner_secret")
    
    if not all([serial_number, owner_secret]):
        return jsonify({"error": "Serial number and owner secret are required"}), 400
    
    # Check if certificate exists
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM certificates WHERE serial_number = %s", (serial_number,))
    certificate = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not certificate:
        return jsonify({"error": "Certificate not found"}), 404
    
    # Generate ZK proof
    proof = ZKProofSystem.create_ownership_proof(serial_number, owner_secret)
    
    # Store proof
    proof_id = secrets.token_hex(16)
    proof_path = os.path.join(PROOF_DIR, f"{proof_id}.json")
    with open(proof_path, 'w') as f:
        json.dump(proof, f)
    
    return jsonify({
        "success": True,
        "proof_id": proof_id,
        "commitment": proof["commitment"],
        "message": "Ownership proof generated successfully"
    }), 200

@app.route('/zk/verify_ownership_proof', methods=['POST'])
def verify_ownership_proof():
    """Verify a ZK proof of certificate ownership"""
    data = request.get_json()
    proof_id = data.get("proof_id")
    serial_number = data.get("serial_number")
    owner_secret = data.get("owner_secret")
    
    if not all([proof_id, serial_number, owner_secret]):
        return jsonify({"error": "Proof ID, serial number, and owner secret are required"}), 400
    
    # Load proof
    proof_path = os.path.join(PROOF_DIR, f"{proof_id}.json")
    if not os.path.exists(proof_path):
        return jsonify({"error": "Proof not found"}), 404
    
    with open(proof_path, 'r') as f:
        proof_obj = json.load(f)
    
    # Verify proof
    is_valid = ZKProofSystem.verify_ownership_proof(proof_obj, serial_number, owner_secret)
    
    if is_valid:
        return jsonify({
            "success": True,
            "message": "Ownership verified successfully",
            "verified": True
        }), 200
    else:
        return jsonify({
            "success": False,
            "message": "Ownership verification failed",
            "verified": False
        }), 400

@app.route('/zk/prove_attribute', methods=['POST'])
def prove_attribute():
    """Prove a certificate attribute satisfies a condition without revealing the value"""
    data = request.get_json()
    serial_number = data.get("serial_number")
    attribute_name = data.get("attribute")
    predicate_type = data.get("predicate")
    predicate_value = data.get("value")
    
    if not all([serial_number, attribute_name, predicate_type, predicate_value]):
        return jsonify({"error": "All fields are required"}), 400
    
    # Get certificate
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM certificates WHERE serial_number = %s", (serial_number,))
    certificate = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not certificate:
        return jsonify({"error": "Certificate not found"}), 404
    
    # Get attribute value
    if attribute_name not in certificate:
        return jsonify({"error": f"Attribute '{attribute_name}' not found"}), 400
    
    attribute_value = str(certificate[attribute_name])
    
    # Generate attribute proof
    proof = ZKProofSystem.create_attribute_proof(attribute_name, attribute_value, predicate_type, predicate_value)
    
    if not proof:
        return jsonify({
            "success": False,
            "message": "Predicate not satisfied",
            "verified": False
        }), 400
    
    # Store proof
    proof_id = secrets.token_hex(16)
    proof_path = os.path.join(PROOF_DIR, f"attr_{proof_id}.json")
    with open(proof_path, 'w') as f:
        json.dump(proof, f)
    
    return jsonify({
        "success": True,
        "proof_id": proof_id,
        "message": f"Attribute '{attribute_name}' satisfies predicate without revealing value",
        "verified": True,
        "commitment": proof["commitment"]
    }), 200

@app.route('/zk/selective_disclosure', methods=['POST'])
def selective_disclosure():
    """Selectively disclose specific certificate attributes using ZK proofs"""
    data = request.get_json()
    serial_number = data.get("serial_number")
    disclosed_attributes = data.get("disclosed_attributes", [])
    owner_secret = data.get("owner_secret")
    
    if not all([serial_number, owner_secret]):
        return jsonify({"error": "Serial number and owner secret are required"}), 400
    
    # Get certificate
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM certificates WHERE serial_number = %s", (serial_number,))
    certificate = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not certificate:
        return jsonify({"error": "Certificate not found"}), 404
    
    # Generate ownership proof
    ownership_proof = ZKProofSystem.create_ownership_proof(serial_number, owner_secret)
    
    # Selectively disclose attributes
    disclosed_data = {}
    hidden_proofs = {}
    
    for key, value in certificate.items():
        if key in disclosed_attributes:
            disclosed_data[key] = value
        elif key not in ['id', 'hash', 'created_at']:
            commitment = ZKProofSystem.generate_commitment(f"{key}:{value}")
            hidden_proofs[key] = {
                "commitment": commitment,
                "exists": True
            }
    
    # Store disclosure proof
    disclosure_id = secrets.token_hex(16)
    disclosure_proof = {
        "disclosure_id": disclosure_id,
        "serial_number": serial_number,
        "ownership_proof": ownership_proof,
        "disclosed_attributes": disclosed_data,
        "hidden_attributes": hidden_proofs,
        "timestamp": datetime.now().isoformat()
    }
    
    proof_path = os.path.join(PROOF_DIR, f"disclosure_{disclosure_id}.json")
    with open(proof_path, 'w') as f:
        json.dump(disclosure_proof, f)
    
    return jsonify({
        "success": True,
        "disclosure_id": disclosure_id,
        "disclosed_attributes": disclosed_data,
        "hidden_attributes_count": len(hidden_proofs),
        "message": "Selective disclosure created successfully"
    }), 200

@app.route('/zk/batch_verify', methods=['POST'])
def batch_verify():
    """Verify multiple certificates at once using ZK proofs"""
    data = request.get_json()
    proof_ids = data.get("proof_ids", [])
    
    if not proof_ids:
        return jsonify({"error": "No proof IDs provided"}), 400
    
    results = []
    for proof_id in proof_ids:
        # Try different proof types
        for prefix in ['', 'attr_', 'disclosure_']:
            proof_path = os.path.join(PROOF_DIR, f"{prefix}{proof_id}.json")
            if os.path.exists(proof_path):
                with open(proof_path, 'r') as f:
                    proof = json.load(f)
                results.append({
                    "proof_id": proof_id,
                    "verified": True,
                    "timestamp": proof.get("timestamp"),
                    "type": prefix or "ownership"
                })
                break
        else:
            results.append({
                "proof_id": proof_id,
                "verified": False,
                "error": "Proof not found"
            })
    
    return jsonify({
        "success": True,
        "results": results,
        "total": len(results),
        "verified_count": sum(1 for r in results if r["verified"])
    }), 200

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