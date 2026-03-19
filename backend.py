from flask import Flask, request, jsonify
import os
import sqlite3
import pandas as pd
import pdfplumber
from dotenv import load_dotenv

# ==============================
# LOAD ENVIRONMENT
# ==============================
load_dotenv()

GEMINI_API_KEY = "AIzaSyBddNFFIkxeKwI7t7PjQ-XBuvAl1gZGs4U"  # os.getenv("GEMINI_API_KEY")

UPLOAD_FOLDER = "uploads"
DB_NAME = "data.db"
TABLE_NAME = "data"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ==============================
# APP INIT
# ==============================
app = Flask(__name__)

# ==============================
# PDF EXTRACTION
# ==============================
def extract_pdf(file):
    rows = []

    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                rows.extend(table[1:])

    if not rows:
        raise Exception("No table found in PDF")

    df = pd.DataFrame(rows)
    df.columns = [f"col_{i}" for i in range(len(df.columns))]
    return df


# ==============================
# FILE LOADER
# ==============================
def load_file(file):

    filename = file.filename.lower()

    if filename.endswith(".csv"):
        df = pd.read_csv(file)

    elif filename.endswith(".xlsx"):
        df = pd.read_excel(file)

    elif filename.endswith(".pdf"):
        df = extract_pdf(file)

    else:
        raise Exception("Unsupported file type")

    if df.empty:
        raise Exception("File is empty")

    df.columns = [
        c.strip().replace(" ", "_").lower()
        for c in df.columns
    ]

    return df


# ==============================
# DATABASE
# ==============================
def save_to_db(df):
    with sqlite3.connect(DB_NAME) as conn:
        df.to_sql(TABLE_NAME, conn,
                  if_exists="replace",
                  index=False)


def run_query(sql):

    if not sql.upper().startswith("SELECT"):
        raise Exception("Only SELECT allowed")

    with sqlite3.connect(DB_NAME) as conn:
        return pd.read_sql(sql, conn)


# ==============================
# ROUTES
# ==============================
@app.route("/")
def home():
    return jsonify({"status": "Backend running 🚀"})


@app.route("/upload", methods=["POST"])
def upload():

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    try:
        file = request.files["file"]
        df = load_file(file)
        save_to_db(df)

        return jsonify({
            "message": "Upload successful",
            "columns": list(df.columns)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/ask", methods=["POST"])
def ask():

    data = request.get_json()

    if not data or "query" not in data:
        return jsonify({"error": "Query missing"}), 400

    try:
        sample = run_query(
            f"SELECT * FROM {TABLE_NAME} LIMIT 5"
        )

        return jsonify({
            "columns": list(sample.columns),
            "rows": sample.to_dict(orient="records")
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==============================
# RUN SERVER
# ==============================
if __name__ == "__main__":
    print("✅ Starting Flask Backend...")
    app.run(
        host="127.0.0.1",   # FIXED
        port=5000,
        debug=True
    )