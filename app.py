import os
import boto3
import pymysql
from flask import Flask, request, render_template_string, redirect, url_for

app = Flask(__name__)

# Fetch configuration from Environment Variables set by User Data
S3_BUCKET = os.environ.get("S3_BUCKET")
DB_HOST = os.environ.get("DB_HOST")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True
    )

def init_db():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS uploads (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    s3_url VARCHAR(512) NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.close()
    except Exception as e:
        print(f"DB Initialization Error: {e}")

# Initialize schema on startup
init_db()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Cloud Vault Live on AWS</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; color: #333; }
        .card { background: #f9f9f9; padding: 20px; border-radius: 8px; border: 1px solid #ddd; width: 450px; margin-bottom: 25px; }
        table { border-collapse: collapse; width: 100%; margin-top: 15px; }
        th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
        th { background-color: #f2f2f2; }
        .btn { background-color: #007bff; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; }
        .btn:hover { background-color: #0056b3; }
    </style>
</head>
<body>
    <h1>Cloud Vault Live on AWS</h1>
    <p><strong>Status:</strong> Connected to MySQL & S3</p>
    
    <div class="card">
        <h3>Upload File to Cloud Vault</h3>
        <form action="/upload" method="POST" enctype="multipart/form-data">
            <input type="file" name="file" required><br><br>
            <button type="submit" class="btn">Upload to S3 & DB</button>
        </form>
    </div>

    <h3>DB Records:</h3>
    {% if records %}
        <table>
            <tr>
                <th>ID</th>
                <th>Filename</th>
                <th>S3 Storage Link</th>
                <th>Uploaded At</th>
            </tr>
            {% for row in records %}
            <tr>
                <td>{{ row[0] }}</td>
                <td>{{ row[1] }}</td>
                <td><a href="{{ row[2] }}" target="_blank">View File</a></td>
                <td>{{ row[3] }}</td>
            </tr>
            {% endfor %}
        </table>
    {% else %}
        <p>() No records found in MySQL database.</p>
    {% endif %}
</body>
</html>
"""

@app.route('/')
def index():
    records = []
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, filename, s3_url, uploaded_at FROM uploads ORDER BY id DESC")
            records = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"Fetch Error: {e}")
    return render_template_string(HTML_TEMPLATE, records=records)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file provided", 400
    file = request.files['file']
    if file.filename == '':
        return "No file selected", 400

    filename = file.filename
    
    # Upload directly to S3
    s3 = boto3.client('s3', region_name=AWS_REGION)
    s3.upload_fileobj(file, S3_BUCKET, filename)
    s3_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{filename}"

    # Insert row into RDS MySQL
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("INSERT INTO uploads (filename, s3_url) VALUES (%s, %s)", (filename, s3_url))
    conn.close()

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
