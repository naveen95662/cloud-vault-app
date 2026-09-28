import os
import traceback
import boto3
import pymysql
from flask import Flask, request, render_template_string, redirect, url_for

app = Flask(__name__)

# Fetch configuration from Environment Variables
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
        autocommit=True,
        connect_timeout=5
    )

def init_db():
    try:
        if DB_HOST and DB_USER and DB_PASSWORD and DB_NAME:
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
        if DB_HOST:
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
        return "No file provided in form request", 400
    file = request.files['file']
    if file.filename == '':
        return "No file selected", 400

    filename = file.filename
    
    try:
        # Pre-check environment variables
        if not S3_BUCKET:
            raise ValueError("Environment variable S3_BUCKET is empty or not set on EC2 instance.")
        if not DB_HOST:
            raise ValueError("Environment variable DB_HOST is empty or not set on EC2 instance.")

        # 1. Upload file directly to S3
        s3 = boto3.client('s3', region_name=AWS_REGION)
        s3.upload_fileobj(
            file, 
            S3_BUCKET, 
            filename,
            ExtraArgs={'ContentType': file.content_type} if file.content_type else {}
        )
        s3_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{filename}"

        # 2. Insert metadata record into MySQL RDS
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO uploads (filename, s3_url) VALUES (%s, %s)", (filename, s3_url))
        conn.close()

        return redirect(url_for('index'))

    except Exception as e:
        # Print full detailed error stack trace directly on the webpage for debugging
        error_trace = traceback.format_exc()
        return f"""
        <html>
            <body style="font-family: monospace; padding: 20px; background-color: #fff0f0;">
                <h2 style="color: #d9534f;">Upload Failed - Error Traceback</h2>
                <p><b>Error Message:</b> {str(e)}</p>
                <hr>
                <h3>Stack Trace:</h3>
                <pre style="background: #f8f8f8; padding: 15px; border: 1px solid #ccc; overflow-x: auto;">{error_trace}</pre>
                <p><a href="/">Return to Main Page</a></p>
            </body>
        </html>
        """, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
