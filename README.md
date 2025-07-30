🛡️ Certificate Authenticator Simulator

🚀 Introduction

Welcome to the **Certificate Authenticator Simulator**! This project is a Python Flask-based web app crafted to help users *easily* verify digital certificates from popular educational platforms—and even your own! 🔍✨

- 🟢 For **Google Education** certificates, simply upload your cert—the app will scan the QR code and *instantly* check if it exists on Google’s platform.
- 📄 For **Great Learning** and **Udemy** certificates, just provide the certificate URL, and the simulator checks its validity online in real-time.
- 🌟 For **Other** platforms, the simulator generates a unique dummy certificate with a secure hash, storing it in a local MySQL database. When you select “Others,” the backend fetches and cross-checks the hash for authenticity.

This tool is perfect for anyone who wants to explore QR code detection, URL validation, and backend hashes in a fun, interactive way. Whether you’re learning, demoing, or just experimenting—this simulator makes the process simple and friendly!

✨ Features

- **Multi-Platform Support:** Validate certificates from Google Education, Great Learning, Udemy, or any other source.
- **QR Code Scanning:** Automagically reads Google certificate QR codes for verification 📷.
- **URL Verification:** Instantly confirms Great Learning & Udemy certificates by their URLs 🌐.
- **Custom Authenticity:** Supports “Others” by hashing and validating certificates in a MySQL database 🗄️.
- **Clean UI:** User-friendly interface guides you every step of the way.
- **Built with Flask:** Lightweight, modular, easy to extend 🍰.

🏗️ How It Works

1. **Upload** your certificate and **choose the organization**.
2. **Google Education:** QR code scanned ➡️ verified via QR data.
3. **Great Learning/Udemy:** Certificate URL is checked online.
4. **Other:** Certificate hash key matches with MySQL database.

🛠️ Getting Started

Prerequisites

- Python 3.x 🐍
- Flask
- MySQL server 🗃️
- Libraries: `qrcode`, `opencv-python`, `mysql-connector-python`, `requests`, etc.

Installation

1. Clone this repo:
   ```bash
   git clone https://github.com/yourusername/certificate-authenticator-simulator.git
   cd certificate-authenticator-simulator
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up the database:
   Use the provided SQL schema in the `/db` folder.

4. Run the app:
   ```bash
   python app.py
   ```

5. **Access it:**  
   Open your browser at [http://localhost:5000](http://localhost:5000) 🚦

🎯 Usage

- Select the issuing organization & upload your certificate.
- For Google Education, ensure the QR code is visible.
- Get real-time feedback: is your certificate genuine? 🕵️♂️

🤝 Contributing

Pull requests and ideas are *always* welcome! Open an issue first for major suggestions.

