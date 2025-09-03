# backend/app.py
import os
import re
import socket
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import psycopg2
from psycopg2.extras import RealDictCursor
import PyPDF2
import docx

# ---------------- Config ----------------
BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

SKILLS = [
    "python", "java", "javascript", "react", "flask", "django", "sql", "excel", "power bi",
    "machine learning", "ml", "aws", "docker", "kubernetes", "c++", "c#", "php", "node",
    "html", "css", "git", "pandas", "numpy", "tensorflow", "pytorch"
]

DB_CONFIG = {
    "host": "localhost",
    "database": "job_portal",
    "user": "sahilpatro",
    "password": "password123"
}

# ---------------- Flask Setup ----------------
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024  # 15MB
CORS(app)

# ---------------- Helpers ----------------
def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print("Database connection failed:", e)
        raise

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(path):
    text_parts = []
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            txt = page.extract_text()
            if txt:
                text_parts.append(txt)
    return "\n".join(text_parts)

def extract_text_from_docx(path):
    try:
        doc = docx.Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except:
        return ""

def extract_text(path):
    ext = path.rsplit(".", 1)[1].lower()
    if ext == "pdf":
        return extract_text_from_pdf(path)
    if ext == "docx":
        return extract_text_from_docx(path)
    with open(path, "r", errors="ignore", encoding="utf-8") as f:
        return f.read()

def find_emails(text):
    return list(set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)))

def find_phones(text):
    candidates = re.findall(r"(\+?\d[\d\-\s]{7,}\d)", text)
    normalized = set()
    for c in candidates:
        digits = re.sub(r"\D", "", c)
        if 7 <= len(digits) <= 15:
            normalized.add(digits)
    return list(normalized)

def find_skills(text):
    t = text.lower()
    return sorted({s for s in SKILLS if s in t})

# ---------------- Database Initialization ----------------
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Jobs table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id SERIAL PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        company VARCHAR(255) NOT NULL,
        location VARCHAR(255),
        description TEXT,
        salary VARCHAR(100),
        posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    # Resumes table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS resumes (
        id SERIAL PRIMARY KEY,
        filename VARCHAR(255) NOT NULL,
        emails TEXT,
        phones TEXT,
        skills TEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database initialized")

# ---------------- API Endpoints ----------------
@app.route("/")
def home():
    return jsonify({"status": "ok", "message": "Flask Job Portal API is running 🚀"})

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs ORDER BY posted_at DESC;")
    jobs = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({"jobs": jobs})

@app.route("/api/jobs", methods=["POST"])
def create_job():
    data = request.get_json() or {}
    if not data.get("title") or not data.get("company"):
        return jsonify({"error": "title and company are required"}), 400
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO jobs (title, company, location, description, salary)
        VALUES (%s, %s, %s, %s, %s) RETURNING *;
    """, (data["title"], data["company"], data.get("location"), data.get("description"), data.get("salary")))
    job = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return jsonify(job), 201

@app.route("/api/jobs/<int:id>", methods=["PUT"])
def update_job(id):
    data = request.get_json()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE jobs SET title=%s, company=%s, location=%s, description=%s, salary=%s
        WHERE id=%s RETURNING *;
    """, (data["title"], data["company"], data.get("location"), data.get("description"), data.get("salary"), id))
    job = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)

@app.route("/api/jobs/<int:id>", methods=["DELETE"])
def delete_job(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM jobs WHERE id=%s RETURNING *;", (id,))
    job = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({"message": "Job deleted"})

@app.route("/api/upload-resume", methods=["POST"])
def upload_resume():
    if "resume" not in request.files:
        return jsonify({"error": "no file part"}), 400
    f = request.files["resume"]
    if f.filename == "":
        return jsonify({"error": "no selected file"}), 400
    if not allowed_file(f.filename):
        return jsonify({"error": "file type not allowed"}), 400

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    filename = secure_filename(f.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    f.save(save_path)

    try:
        text = extract_text(save_path)
    except Exception as e:
        return jsonify({"error": "failed to parse file", "details": str(e)}), 500

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO resumes (filename, emails, phones, skills)
        VALUES (%s, %s, %s, %s) RETURNING *;
    """, (filename, ",".join(find_emails(text)), ",".join(find_phones(text)), ",".join(find_skills(text))))
    resume = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "filename": filename,
        "emails": find_emails(text),
        "phones": find_phones(text),
        "skills": find_skills(text),
        "text": text[:4000]
    })

# ---------------- Dynamic port finder ----------------
def find_free_port(start=5000, max_port=5100):
    port = start
    while port <= max_port:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", port)) != 0:
                return port
        port += 1
    raise RuntimeError("No free ports available in range")

# ---------------- Run App ----------------
if __name__ == "__main__":
    init_db()  # initialize tables if not exists
    port = find_free_port()
    print(f"✅ Flask server running at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
