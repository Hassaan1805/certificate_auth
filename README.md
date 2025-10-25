# Certificate Authenticator Backend

This is the Flask backend for the Certificate Authenticator feature integrated into the DIDfinal project.

## Prerequisites

- Python 3.8+
- MySQL database
- Required Python packages (see requirements below)

## Installation

1. **Install Python dependencies:**

```bash
pip install flask pytesseract pillow mysql-connector-python reportlab requests opencv-python-headless numpy PyMuPDF PyPDF2
```

2. **Install Tesseract OCR:**
   - Windows: Download and install from https://github.com/UB-Mannheim/tesseract/wiki
   - Linux: `sudo apt-get install tesseract-ocr`
   - Mac: `brew install tesseract`

3. **Set up MySQL database:**

Create a database and table:

```sql
CREATE DATABASE certificate_auth;

USE certificate_auth;

CREATE TABLE certificates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    serial_number VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    organization VARCHAR(255) NOT NULL,
    issue_date DATE NOT NULL,
    expiry_date DATE NOT NULL,
    completion_date DATE NOT NULL,
    issuer VARCHAR(255) NOT NULL,
    hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

4. **Update database configuration in `auth.py`:**

```python
db_config = {
    'user': 'your_username',
    'password': 'your_password',
    'host': 'localhost',
    'database': 'certificate_auth'
}
```

## Running the Backend

1. Navigate to the certificate_backend directory:
```bash
cd "e:\projects\Random Projects\DIDfinal\certificate_backend"
```

2. Run the Flask server:
```bash
python auth.py
```

The server will start on `http://127.0.0.1:5000`

## API Endpoints

### Generate Certificate
- **POST** `/generate`
- Creates a new certificate PDF and stores it in the database
- Body: form-data with name, organization, issue_date, expiry_date, completion_date, issuer, serial_number

### Authenticate Certificate
- **POST** `/authenticate`
- Verifies a certificate by serial number
- Body: form-data with serial_number

### Upload Certificate (Generic)
- **POST** `/upload`
- Extracts data from uploaded certificate and verifies
- Body: form-data with file

### Upload Udemy Certificate
- **POST** `/upload_udemy`
- Verifies Udemy certificates by checking URL validity
- Body: form-data with file

### Upload Great Learning Certificate
- **POST** `/upload_great_learning`
- Verifies Great Learning certificates by checking URL validity
- Body: form-data with file

### Upload Google Education Certificate
- **POST** `/upload_google_education`
- Verifies Google Education certificates by scanning QR codes
- Body: form-data with file

### Download Certificate
- **GET** `/download?file={filename}`
- Downloads a generated certificate

### Delete Certificate
- **POST** `/delete`
- Removes a certificate file
- Body: form-data with file_name

## Integration with Frontend

The React frontend (`CertificatesPage.tsx`) is configured to connect to this backend at `http://127.0.0.1:5000`.

To access the Certificates page:
1. Start the Flask backend (this server)
2. Start the React frontend: `cd portal && npm run dev`
3. Navigate to `http://localhost:5173/certificates` in your browser

## Features

- **Certificate Generation**: Create official certificates with unique serial numbers and cryptographic hashes
- **Certificate Authentication**: Verify certificates using serial numbers or file uploads
- **Multi-Platform Support**: Verify certificates from Udemy, Great Learning, and Google Education
- **OCR Support**: Extract text from certificate images using Tesseract
- **QR Code Scanning**: Validate Google Education certificates via QR codes
- **Secure Storage**: Store certificate metadata in MySQL database with SHA-256 hashes

## File Structure

```
certificate_backend/
├── auth.py                 # Main Flask application
├── certificates/           # Generated/uploaded certificates
├── static/                 # Static CSS files
├── templates/              # HTML templates (standalone pages)
├── db_sample.txt          # Database schema reference
└── README.md              # This file
```

## CORS Configuration

If you encounter CORS issues, install flask-cors:

```bash
pip install flask-cors
```

Add to `auth.py`:
```python
from flask_cors import CORS
CORS(app)
```

## Troubleshooting

1. **Database Connection Error**: Ensure MySQL is running and credentials are correct
2. **Tesseract Not Found**: Make sure Tesseract OCR is installed and in your system PATH
3. **Port Already in Use**: Change the port in auth.py: `app.run(debug=True, port=5001)`
4. **CORS Errors**: Add CORS support as mentioned above

## Security Notes

- This is a development setup. For production:
  - Use environment variables for database credentials
  - Enable HTTPS
  - Implement rate limiting
  - Add authentication/authorization
  - Validate all inputs
  - Use production WSGI server (gunicorn, uwsgi)
