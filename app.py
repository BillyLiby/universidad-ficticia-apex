import csv
import io
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, Response)
from config import SECRET_KEY
from db import get_db, hash_password

app = Flask(__name__)
app.secret_key = SECRET_KEY


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


@app.route("/")
@login_required
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        conn = get_db()
        try:
            conn.execute("INSERT INTO users (email, password_hash) VALUES (?,?)",
                         (email, hash_password(password)))
            conn.commit()
            flash("Usuario registrado. Inicia sesión.")
            return redirect(url_for("login"))
        except Exception:
            flash("No se pudo registrar el usuario.")
        finally:
            conn.close()
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        if user and user["password_hash"] == hash_password(password):
            session["user"] = user["email"]
            session["role"] = user["role"]
            return redirect(url_for("home"))
        flash("Credenciales incorrectas.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/search")
@login_required
def search():
    q = request.args.get("q", "")
    results = []
    if q:
        conn = get_db()
        like = f"%{q}%"
        results = conn.execute(
            "SELECT * FROM students WHERE first_name LIKE ? OR last_name LIKE ? OR student_id LIKE ?",
            (like, like, like)).fetchall()
        conn.close()
    return render_template("search.html", q=q, results=results)


@app.route("/expediente/<student_id>")
@login_required
def expediente(student_id):
    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
    grades = conn.execute("SELECT * FROM grades WHERE student_id = ?", (student_id,)).fetchall()
    conn.close()
    return render_template("expediente.html", student=student, grades=grades)


@app.route("/comments", methods=["GET", "POST"])
@login_required
def comments():
    conn = get_db()
    if request.method == "POST":
        conn.execute("INSERT INTO comments (author, body) VALUES (?,?)",
                     (session["user"], request.form["body"]))
        conn.commit()
    rows = conn.execute("SELECT * FROM comments ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("comments.html", comments=rows)


@app.route("/report")
@login_required
def report():
    conn = get_db()
    rows = conn.execute(
        "SELECT s.student_id, s.first_name, s.last_name, g.course, g.grade "
        "FROM students s JOIN grades g ON s.student_id = g.student_id").fetchall()
    conn.close()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["student_id", "nombre", "apellido", "curso", "nota"])
    for r in rows:
        writer.writerow(list(r))
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=reporte.csv"})


if __name__ == "__main__":
    app.run(debug=False)
