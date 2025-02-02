from flask import Flask, request, send_file, jsonify, send_from_directory
from PIL import Image, ImageDraw, ImageFont
import hashlib
import os
import json
import mysql.connector as msql

app = Flask(__name__)

# Database Connection
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "tiger",
    "database": "certificate_db"
}

db = msql.connect(**DB_CONFIG)
cursor = db.cursor()

# Ensure database and table exist
cursor.execute("CREATE DATABASE IF NOT EXISTS certificate_db")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS certificates (
        id INT AUTO_INCREMENT PRIMARY KEY,
        serial_number VARCHAR(255) UNIQUE NOT NULL,
        hash_value VARCHAR(255) NOT NULL
    )
""")
db.commit()

# Constants
OUTPUT_DIR = "certificates"
FONT_PATH = "arial.ttf"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def insert_certificate(serial_number, hash_value):
    """Insert certificate hash into database."""
    cursor.execute("""
        INSERT INTO certificates (serial_number, hash_value)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE hash_value = VALUES(hash_value)
    """, (serial_number, hash_value))
    db.commit()

def check_hash(serial_number, hash_value):
    """Check if a hash exists in the database."""
    cursor.execute("SELECT hash_value FROM certificates WHERE serial_number = %s", (serial_number,))
    result = cursor.fetchone()
    return result and result[0] == hash_value

def create_certificate_template(name, organization, issue_date, expiry_date, serial_number):
    """Generate the certificate image and SHA-256 hash."""
    width, height = 2480, 3508
    cert_image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(cert_image)
    
    font_large = ImageFont.truetype(FONT_PATH, 100)
    font_medium = ImageFont.truetype(FONT_PATH, 60)
    font_small = ImageFont.truetype(FONT_PATH, 40)
    
    draw.text((width // 4, 300), "Certificate of Achievement", fill="black", font=font_large)
    draw.text((width // 4, 600), f"Awarded to: {name}", fill="black", font=font_medium)
    draw.text((width // 4, 750), f"Organization: {organization}", fill="black", font=font_medium)
    draw.text((width // 4, 900), f"Issue Date: {issue_date} | Expiry Date: {expiry_date}", fill="black", font=font_small)
    draw.text((width // 4, 1000), f"Serial Number: {serial_number}", fill="black", font=font_small)
    
    cert_data = f"{name}|{organization}|{issue_date}|{expiry_date}|{serial_number}"
    cert_hash = hashlib.sha256(cert_data.encode()).hexdigest()
    
    draw.text((width // 4, 1100), f"Hash: {cert_hash[:20]}...", fill="black", font=font_small)
    return cert_image, cert_hash

@app.route('/generate', methods=['POST'])
def generate():
    """Generate a certificate and store its hash in the database."""
    data = request.json
    required_fields = ["name", "organization", "issue_date", "expiry_date", "serial_number"]
    if not all(field in data and data[field] for field in required_fields):
        return jsonify({"error": "All fields are required"}), 400

    cert_image, cert_hash = create_certificate_template(
        data["name"], data["organization"], data["issue_date"], data["expiry_date"], data["serial_number"]
    )

    cert_filename = f"{OUTPUT_DIR}/certificate_{data['serial_number']}.png"
    cert_image.save(cert_filename)
    
    insert_certificate(data['serial_number'], cert_hash)
    
    return send_file(cert_filename, mimetype='image/png')

@app.route('/authenticate', methods=['POST'])
def authenticate():
    """Authenticate a certificate by checking if its hash exists."""
    data = request.json
    serial_number = data.get("serial_number")
    
    if not serial_number:
        return jsonify({"error": "Serial number is required"}), 400
    
    cursor.execute("SELECT hash_value FROM certificates WHERE serial_number = %s", (serial_number,))
    result = cursor.fetchone()
    
    if result:
        return jsonify({"message": "Certificate is legitimate", "serial_number": serial_number, "hash": result[0]}), 200
    else:
        return jsonify({"error": "Certificate not found or invalid"}), 404

if __name__ == '__main__':
    app.run(debug=True)
