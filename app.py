import csv
import io
import os
import re
import subprocess
import zipfile
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, Response)
from config import SECRET_KEY
from db import get_db, hash_password
import validators as v

app = Flask(__name__)
app.secret_key = SECRET_KEY

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


@app.after_request
def security_headers(resp):
    # Defensa en profundidad: aunque algún dato llegara sin codificar, el navegador
    # no ejecuta scripts en línea ni manejadores onerror/onclick.
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


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
    conn = get_db()
    counts = {
        "students": conn.execute("SELECT COUNT(*) FROM students").fetchone()[0],
        "sedes": conn.execute("SELECT COUNT(*) FROM sedes").fetchone()[0],
        "courses": conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0],
        "carreras": conn.execute("SELECT COUNT(*) FROM carreras").fetchone()[0],
    }
    conn.close()
    return render_template("home.html", counts=counts)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if not v.valid_email(email) or not v.valid_password(password):
            flash("Correo inválido o contraseña débil (mín. 8 caracteres, letras y números).", "error")
            return render_template("register.html")
        conn = get_db()
        try:
            conn.execute("INSERT INTO users (email, password_hash) VALUES (?,?)",
                         (email, hash_password(password)))
            conn.commit()
            flash("Usuario registrado. Inicia sesión.")
            return redirect(url_for("login"))
        except Exception:
            flash("No se pudo registrar el usuario.", "error")
        finally:
            conn.close()
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if not v.valid_email(email) or len(password) > 128:
            flash("Credenciales incorrectas.", "error")
            return render_template("login.html")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        if user and user["password_hash"] == hash_password(password):
            session["user"] = user["email"]
            session["role"] = user["role"]
            return redirect(url_for("home"))
        flash("Credenciales incorrectas.", "error")
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
    if q and not v.valid_search(q):
        flash("Parámetro de búsqueda inválido.", "error")
        return render_template("search.html", q="", results=[])
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
    if not v.valid_student_id(student_id):
        flash("Identificador de estudiante inválido.", "error")
        return redirect(url_for("students"))
    conn = get_db()
    student = conn.execute(
        "SELECT s.*, se.name AS sede, ca.name AS carrera FROM students s "
        "LEFT JOIN sedes se ON s.sede_id = se.id LEFT JOIN carreras ca ON s.carrera_id = ca.id "
        "WHERE s.student_id = ?", (student_id,)).fetchone()
    grades = conn.execute(
        "SELECT g.course, g.grade, c.code, c.ciclo FROM grades g LEFT JOIN courses c ON c.name = g.course "
        "WHERE g.student_id = ? ORDER BY c.ciclo, g.course", (student_id,)).fetchall()
    conn.close()
    return render_template("expediente.html", student=student, grades=grades)


@app.route("/comments", methods=["GET", "POST"])
@login_required
def comments():
    conn = get_db()
    if request.method == "POST" and not v.valid_comment(request.form["body"]):
        flash("Comentario vacío o demasiado largo (máx. 500 caracteres).", "error")
    elif request.method == "POST":
        conn.execute("INSERT INTO comments (author, body) VALUES (?,?)",
                     (session["user"], request.form["body"]))
        conn.commit()
    rows = conn.execute("SELECT * FROM comments ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("comments.html", comments=rows)


@app.route("/students")
@login_required
def students():
    sede = v.int_param(request.args.get("sede", ""))
    carrera = v.int_param(request.args.get("carrera", ""))
    conn = get_db()
    sedes = conn.execute("SELECT * FROM sedes ORDER BY name").fetchall()
    carreras = conn.execute("SELECT * FROM carreras ORDER BY name").fetchall()
    sql = ("SELECT s.student_id, s.first_name, s.last_name, s.email, s.ciclo, "
           "se.name AS sede, ca.name AS carrera FROM students s "
           "LEFT JOIN sedes se ON s.sede_id = se.id LEFT JOIN carreras ca ON s.carrera_id = ca.id")
    where, params = [], []
    if sede is not None:
        where.append("s.sede_id = ?"); params.append(sede)
    if carrera is not None:
        where.append("s.carrera_id = ?"); params.append(carrera)
    if where:
        sql += " WHERE " + " AND ".join(where)
    rows = conn.execute(sql + " ORDER BY s.last_name, s.first_name", params).fetchall()
    conn.close()
    return render_template("students.html", students=rows, sedes=sedes, carreras=carreras,
                           sede=sede, carrera=carrera)


@app.route("/sedes")
@login_required
def sedes():
    conn = get_db()
    rows = conn.execute(
        "SELECT se.id, se.name, se.city, COUNT(s.id) AS total FROM sedes se "
        "LEFT JOIN students s ON s.sede_id = se.id GROUP BY se.id ORDER BY se.name").fetchall()
    conn.close()
    return render_template("sedes.html", sedes=rows)


@app.route("/carreras")
@login_required
def carreras():
    conn = get_db()
    rows = conn.execute(
        "SELECT ca.id, ca.code, ca.name, COUNT(DISTINCT s.id) AS estudiantes, "
        "(SELECT COUNT(*) FROM courses c WHERE c.carrera_id = ca.id) AS cursos "
        "FROM carreras ca LEFT JOIN students s ON s.carrera_id = ca.id GROUP BY ca.id ORDER BY ca.name").fetchall()
    conn.close()
    return render_template("carreras.html", carreras=rows)


@app.route("/carreras/<int:carrera_id>")
@login_required
def carrera(carrera_id):
    conn = get_db()
    ca = conn.execute("SELECT * FROM carreras WHERE id = ?", (carrera_id,)).fetchone()
    cursos = conn.execute("SELECT * FROM courses WHERE carrera_id = ? ORDER BY ciclo, name", (carrera_id,)).fetchall()
    conn.close()
    return render_template("carrera.html", carrera=ca, cursos=cursos)


@app.route("/courses")
@login_required
def courses():
    carrera = v.int_param(request.args.get("carrera", ""))
    conn = get_db()
    carreras = conn.execute("SELECT * FROM carreras ORDER BY name").fetchall()
    sql = ("SELECT c.code, c.name, c.ciclo, ca.name AS carrera, COUNT(g.id) AS inscritos, "
           "ROUND(AVG(g.grade), 1) AS promedio FROM courses c JOIN carreras ca ON c.carrera_id = ca.id "
           "LEFT JOIN grades g ON g.course = c.name")
    params = []
    if carrera is not None:
        sql += " WHERE c.carrera_id = ?"; params.append(carrera)
    rows = conn.execute(sql + " GROUP BY c.id ORDER BY ca.name, c.ciclo, c.name", params).fetchall()
    conn.close()
    return render_template("courses.html", courses=rows, carreras=carreras, carrera=carrera)


@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    if session.get("role") != "admin":
        return "Acceso denegado", 403
    conn = get_db()
    try:
        if request.method == "POST":
            form = request.form.get("form")
            if form == "student":
                sid, fn, ln, em = (request.form.get(k, "") for k in ("student_id", "first_name", "last_name", "email"))
                sede_id = v.int_param(request.form.get("sede_id", ""))
                carrera_id = v.int_param(request.form.get("carrera_id", ""))
                ciclo = v.valid_ciclo(request.form.get("ciclo", ""))
                sede_ok = sede_id is not None and conn.execute("SELECT 1 FROM sedes WHERE id = ?", (sede_id,)).fetchone()
                carrera_ok = carrera_id is not None and conn.execute("SELECT 1 FROM carreras WHERE id = ?", (carrera_id,)).fetchone()
                if not (v.valid_student_id(sid) and v.valid_name(fn) and v.valid_name(ln) and v.valid_email(em)
                        and sede_ok and carrera_ok and ciclo):
                    flash("Datos de estudiante inválidos.", "error")
                else:
                    try:
                        conn.execute("INSERT INTO students (student_id, first_name, last_name, email, sede_id, carrera_id, ciclo) "
                                     "VALUES (?,?,?,?,?,?,?)", (sid, fn, ln, em, sede_id, carrera_id, ciclo))
                        conn.commit()
                        flash("Estudiante agregado.")
                    except Exception:
                        flash("No se pudo guardar el registro.", "error")
            elif form == "grade":
                sid = request.form.get("student_id", "")
                course = request.form.get("course", "")
                grade = v.valid_grade(request.form.get("grade"))
                ok = (v.valid_student_id(sid) and v.valid_name(course) and grade is not None
                      and conn.execute("SELECT 1 FROM students WHERE student_id = ?", (sid,)).fetchone()
                      and conn.execute("SELECT 1 FROM courses WHERE name = ?", (course,)).fetchone())
                if not ok:
                    flash("Datos de calificación inválidos (estudiante y curso existentes, nota entre 0 y 100).", "error")
                else:
                    conn.execute("INSERT INTO grades (student_id, course, grade) VALUES (?,?,?)", (sid, course, grade))
                    conn.commit()
                    flash("Calificación agregada.")
        sedes_rows = conn.execute("SELECT * FROM sedes ORDER BY name").fetchall()
        carreras_rows = conn.execute("SELECT * FROM carreras ORDER BY name").fetchall()
    finally:
        conn.close()
    return render_template("admin.html", sedes=sedes_rows, carreras=carreras_rows)


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


def build_report_csv():
    """Genera el CSV del reporte académico y lo deja en disco como report.csv."""
    conn = get_db()
    rows = conn.execute(
        "SELECT s.student_id, s.first_name, s.last_name, g.course, g.grade "
        "FROM students s JOIN grades g ON s.student_id = g.student_id").fetchall()
    conn.close()
    path = os.path.join(BASE_DIR, "report.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["student_id", "nombre", "apellido", "curso", "nota"])
        for r in rows:
            writer.writerow(list(r))
    return path


# =====================================================================
# LABORATORIO FASE I-D: compresión del reporte VULNERABLE a inyección de
# comandos (solo laboratorio, datos ficticios, servidor local). Se corrige
# en el siguiente commit.
# =====================================================================
@app.route("/lab/compress", methods=["GET", "POST"])
@login_required
def lab_compress():
    cmd_shown, output, error = None, None, None
    if request.method == "POST":
        filename = request.form.get("filename", "")
        build_report_csv()
        # VULNERABLE: el nombre que escribe el usuario se concatena dentro de una
        # cadena que luego se pasa a una shell del sistema operativo (shell=True).
        # El sistema ya no distingue entre "nombre de archivo" y "otro comando".
        cmd = "copy report.csv reports\\" + filename + ".zip"
        cmd_shown = cmd
        try:
            result = subprocess.run(cmd, shell=True, cwd=BASE_DIR,
                                    capture_output=True, text=True, timeout=10)
            output = (result.stdout or "") + (result.stderr or "")
        except Exception as e:
            error = str(e)
    files = sorted(os.listdir(REPORTS_DIR))
    return render_template("lab_compress.html", cmd=cmd_shown, output=output, error=error,
                           files=files, vulnerable=True)


# =====================================================================
# LABORATORIO FASE I-B: consulta CORREGIDA con parámetros (sentencia preparada).
# Se mantiene sin validar la entrada a propósito, para demostrar que la
# parametrización por sí sola impide alterar la estructura SQL.
# =====================================================================
@app.route("/lab/search")
@login_required
def lab_search():
    q = request.args.get("q", "")
    # CORREGIDO: la sentencia es fija; el dato viaja aparte como parámetro
    sql = ("SELECT student_id, first_name, last_name, email FROM students "
           "WHERE first_name LIKE ? OR last_name LIKE ?")
    like = f"%{q}%"
    params = (like, like)
    rows, cols, error = [], [], None
    if q:
        conn = get_db()
        try:
            cur = conn.execute(sql, params)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
        except Exception:
            error = "No se pudo completar la búsqueda."
        finally:
            conn.close()
    return render_template("lab_search.html", q=q, sql=sql if q else "", params=params if q else None,
                           rows=rows, cols=cols, error=error, vulnerable=False)


# =====================================================================
# LABORATORIO FASE I-C: salida CORREGIDA contra XSS (codificación de salida
# contextual + textContent en el cliente + CSP como defensa en profundidad).
# =====================================================================
@app.route("/lab/xss")
@login_required
def lab_xss():
    q = request.args.get("q", "")
    conn = get_db()
    rows = conn.execute("SELECT * FROM comments ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("lab_xss.html", q=q, comments=rows, vulnerable=False)


if __name__ == "__main__":
    app.run(debug=False)
