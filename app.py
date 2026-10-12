import os
import sqlite3
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, flash, g, redirect, render_template, request, url_for

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")
app.config["DB_PATH"] = os.getenv("DB_PATH", "zhkh.db")

CATEGORIES = [
    "Авария",
    "Сантехника",
    "Электрика",
    "Лифт",
    "Уборка и двор",
    "Начисления и оплата",
    "Иное",
]


@app.context_processor
def inject_globals():
    return {
        "app_name": os.getenv("APP_NAME", "ЖКХ Заявки"),
        "categories": CATEGORIES,
    }


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DB_PATH"])
        g.db.row_factory = sqlite3.Row

    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(app.config["DB_PATH"])
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            address TEXT NOT NULL,
            phone TEXT,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'new',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


@app.route("/")
def index():
    db = get_db()

    total = db.execute("SELECT COUNT(*) AS c FROM requests").fetchone()["c"]
    new = db.execute(
        "SELECT COUNT(*) AS c FROM requests WHERE status = 'new'"
    ).fetchone()["c"]

    return render_template("index.html", total=total, new=new)


@app.route("/requests")
def requests_list():
    db = get_db()
    items = db.execute(
        """
        SELECT id, full_name, address, phone, category, description, status, created_at
        FROM requests
        ORDER BY id DESC
        """
    ).fetchall()

    return render_template("requests.html", requests=items)


@app.route("/requests/new", methods=["GET", "POST"])
def request_new():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        address = request.form.get("address", "").strip()
        phone = request.form.get("phone", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()

        errors = []

        if not full_name:
            errors.append("Укажите ФИО.")

        if not address:
            errors.append("Укажите адрес.")

        if category not in CATEGORIES:
            errors.append("Выберите категорию заявки.")

        if not description:
            errors.append("Опишите проблему.")

        if errors:
            for error in errors:
                flash(error, "error")

            return render_template("new_request.html", form=request.form)

        db = get_db()
        db.execute(
            """
            INSERT INTO requests (
                full_name,
                address,
                phone,
                category,
                description,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                full_name,
                address,
                phone,
                category,
                description,
                "new",
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ),
        )
        db.commit()

        flash("Заявка успешно отправлена.", "success")
        return redirect(url_for("requests_list"))

    return render_template("new_request.html", form={})


@app.route("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_RUN_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_RUN_PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
    )
