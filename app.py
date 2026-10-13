"""
ShortLink - a simple self-hosted URL shortener.
Run:  python app.py        (dev, http://localhost:5000)
Prod: gunicorn app:app     (see README.md for hosting steps)
"""
import os
import re
import secrets
import sqlite3
import string
from datetime import datetime, timezone
from io import BytesIO

from flask import Flask, g, jsonify, redirect, render_template, request, send_file

import qrcode

app = Flask(__name__)

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "links.db"))
BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")  # e.g. https://links.example.com

CODE_ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6
CUSTOM_ALIAS_RE = re.compile(r"^[A-Za-z0-9_-]{3,30}$")


# ---------- database ----------

def get_db():
    db = getattr(g, "_db", None)
    if db is None:
        db = g._db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db


def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS links (
                   code TEXT PRIMARY KEY,
                   url TEXT NOT NULL,
                   created_at TEXT NOT NULL,
                   clicks INTEGER NOT NULL DEFAULT 0,
                   last_clicked TEXT
               )"""
        )


@app.teardown_appcontext
def close_db(_exc):
    db = getattr(g, "_db", None)
    if db is not None:
        db.close()


# ---------- helpers ----------

def base_url():
    if BASE_URL:
        return BASE_URL
    # request.host_url ends with "/"
    return request.host_url.rstrip("/")


def normalize_url(url: str) -> str:
    url = url.strip()
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url
    return url


def valid_url(url: str) -> bool:
    return re.match(r"^https?://[^\s/$.?#].[^\s]*$", url, re.IGNORECASE) is not None


def generate_code() -> str:
    db = get_db()
    for _ in range(20):  # practically never collides twice
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        if not db.execute("SELECT 1 FROM links WHERE code = ?", (code,)).fetchone():
            return code
    raise RuntimeError("could not generate a unique code")


# ---------- routes ----------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/shorten", methods=["POST"])
def shorten():
    data = request.get_json(force=True, silent=True) or {}
    url = normalize_url(data.get("url", ""))
    if not valid_url(url):
        return jsonify({"error": "Please enter a valid URL, e.g. https://example.com/page"}), 400

    custom = (data.get("custom") or "").strip()
    db = get_db()

    if custom:
        if not CUSTOM_ALIAS_RE.match(custom):
            return jsonify({"error": "Custom name must be 3-30 characters: letters, numbers, - or _"}), 400
        if db.execute("SELECT 1 FROM links WHERE code = ?", (custom,)).fetchone():
            return jsonify({"error": "That custom name is already taken"}), 409
        code = custom
    else:
        code = generate_code()

    db.execute(
        "INSERT INTO links (code, url, created_at) VALUES (?, ?, ?)",
        (code, url, datetime.now(timezone.utc).isoformat()),
    )
    db.commit()
    return jsonify({"code": code, "short_url": f"{base_url()}/{code}", "url": url})


@app.route("/api/links")
def list_links():
    db = get_db()
    rows = db.execute(
        "SELECT code, url, created_at, clicks, last_clicked FROM links ORDER BY created_at DESC"
    ).fetchall()
    return jsonify([
        {
            "code": r["code"],
            "url": r["url"],
            "short_url": f"{base_url()}/{r['code']}",
            "created_at": r["created_at"],
            "clicks": r["clicks"],
            "last_clicked": r["last_clicked"],
        }
        for r in rows
    ])


@app.route("/api/links/<code>", methods=["DELETE"])
def delete_link(code):
    db = get_db()
    cur = db.execute("DELETE FROM links WHERE code = ?", (code,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify({"error": "not found"}), 404
    return jsonify({"ok": True})


@app.route("/qr/<code>.png")
def qr_code(code):
    db = get_db()
    row = db.execute("SELECT 1 FROM links WHERE code = ?", (code,)).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    img = qrcode.make(f"{base_url()}/{code}")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/<code>")
def go(code):
    # only redirect real codes; let unknown paths 404 quietly
    if not re.match(r"^[A-Za-z0-9_-]{1,30}$", code):
        return "Not found", 404
    db = get_db()
    row = db.execute("SELECT url FROM links WHERE code = ?", (code,)).fetchone()
    if not row:
        return render_template("index.html", missing=code), 404
    db.execute(
        "UPDATE links SET clicks = clicks + 1, last_clicked = ? WHERE code = ?",
        (datetime.now(timezone.utc).isoformat(), code),
    )
    db.commit()
    return redirect(row["url"], code=302)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

