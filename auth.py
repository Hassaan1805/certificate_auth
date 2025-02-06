from flask import Flask, request, render_template, jsonify, send_file
import hashlib
import json
import os
from datetime import datetime

app = Flask(__name__)

OUTPUT_DIR = "certificates"  # Folder to store generated certificates
CERTIFICATE_METADATA_FILE = "certificate_metadata.json"  # File to store certificate metadata

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load the metadata from the JSON file or initialize an empty dictionary
if os.path.exists(CERTIFICATE_METADATA_FILE):
    with open(CERTIFICATE_METADATA_FILE, "r") as f:
        certificate_metadata = json.load(f)
else:
    certificate_metadata = {}

@app.route('/')
def index():
    return render_template("index.html")

def generate_certificate(name, organization, issue_date, expiry_date, serial_number):
    try:
        # Certificate Text Template
        certificate_text = f"""
        -----------------------------------------
                CERTIFICATE OF ACHIEVEMENT
        -----------------------------------------

        This is to certify that

        Name: {name}
        Organization: {organization}

        Has successfully completed the requirements
        of the program and is awarded this certificate.

        Issue Date: {issue_date}
        Expiry Date: {expiry_date}
        Serial Number: {serial_number}

        Certificate Issued On: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

        -----------------------------------------
        """

        # Generate SHA-256 hash for verification
        cert_data = f"{name}|{organization}|{issue_date}|{expiry_date}|{serial_number}"
        cert_hash = hashlib.sha256(cert_data.encode()).hexdigest()

        # Add hash to certificate text
        certificate_text += f"Certificate Hash: {cert_hash[:20]}...\n"  # Shortened hash

        # Save the certificate to a text file
        cert_filename = f"{OUTPUT_DIR}/certificate_{serial_number}.txt"
        with open(cert_filename, "w") as file:
            file.write(certificate_text)

        # Store metadata for future verification
        certificate_metadata[serial_number] = {
            "name": name,
            "organization": organization,
            "issue_date": issue_date,
            "expiry_date": expiry_date,
            "serial_number": serial_number,
            "hash": cert_hash
        }

        # Save metadata to a JSON file (used as a persistent storage)
        with open(CERTIFICATE_METADATA_FILE, "w") as f:
            json.dump(certificate_metadata, f)

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
    serial_number = request.form.get("serial_number")

    if not all([name, organization, issue_date, expiry_date, serial_number]):
        return jsonify({"error": "All fields are required"}), 400

    cert_html = generate_certificate(name, organization, issue_date, expiry_date, serial_number)
    if not cert_html:
        return jsonify({"error": "Failed to generate certificate"}), 500

    return jsonify({"success": True, "file_path": f"certificate_{serial_number}.txt"})




@app.route('/authenticate', methods=['POST'])
def authenticate():
    serial_number = request.form.get("serial_number")

    if not serial_number:
        return jsonify({"error": "Serial number is required"}), 400

    metadata = certificate_metadata.get(serial_number)
    if not metadata:
        return jsonify({"error": "Certificate not found"}), 404

    # Retrieve stored hash and verify
    stored_hash = metadata.get("hash")
    if stored_hash:
        return jsonify({"message": "Certificate is authentic"}), 200
    else:
        return jsonify({"error": "Certificate is not authentic"}), 400
@app.route('/download')
def download():
    file_name = request.args.get('file')
    file_path = os.path.join(OUTPUT_DIR, file_name)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({"error": "File not found"}), 404
if __name__ == '__main__':
    app.run(debug=True)
