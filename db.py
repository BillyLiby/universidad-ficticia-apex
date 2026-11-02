import sqlite3
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from config import DB_PATH

# CORREGIDO (Fase II-A): Argon2id en vez de SHA-256 simple.
# Argon2id es una Key Derivation Function: lenta a propósito, usa memoria
# además de CPU (dificulta ataques con GPU/ASIC) y genera una sal aleatoria
# distinta por cada hash, incluida automáticamente dentro del propio hash.
_ph = PasswordHasher()  # parámetros por defecto: tiempo, memoria y paralelismo


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password):
    """Genera un hash Argon2id del password. La sal se genera sola y queda
    codificada dentro del propio hash (no se guarda en una columna aparte)."""
    return _ph.hash(password)


def verify_password(password, stored_hash):
    """Verifica un password contra un hash Argon2id. Devuelve True/False y
    nunca compara cadenas directamente (evita ataques de temporización)."""
    try:
        return _ph.verify(stored_hash, password)
    except (VerifyMismatchError, InvalidHashError, ValueError):
        return False


CARRERAS = [
    (1, "SIS", "Ingeniería en Sistemas"),
    (2, "CIB", "Ingeniería en Ciberseguridad"),
    (3, "ADM", "Administración de Empresas"),
]
# Pensum: carrera -> ciclo -> cursos
PENSUM = {
    1: {1: ["Introducción a la Programación", "Matemática Discreta"],
        2: ["Programación Orientada a Objetos", "Estructuras de Datos"],
        3: ["Bases de Datos", "Redes"],
        4: ["Ingeniería de Software", "Sistemas Operativos"]},
    2: {1: ["Fundamentos de Ciberseguridad", "Lógica y Programación"],
        2: ["Redes de Computadoras", "Criptografía Básica"],
        3: ["Seguridad de Aplicaciones", "Seguridad en Redes"],
        4: ["Análisis Forense Digital", "Gestión de Riesgos"]},
    3: {1: ["Introducción a la Administración", "Contabilidad General"],
        2: ["Estadística Aplicada", "Mercadotecnia"],
        3: ["Finanzas Corporativas", "Gestión del Talento Humano"],
        4: ["Planeación Estratégica", "Administración de Proyectos"]},
}
# (student_id, nombre, apellido, correo, sede_id, carrera_id, ciclo actual)
STUDENTS = [
    ("2026001", "Ana", "Lopez", "ana@uni.test", 1, 1, 3),
    ("2026002", "Carlos", "Perez", "carlos@uni.test", 1, 1, 2),
    ("2026003", "Maria", "Gomez", "maria@uni.test", 2, 2, 4),
    ("2026004", "Luis", "Ruiz", "luis@uni.test", 2, 3, 1),
    ("2026005", "Sofia", "Castillo", "sofia@uni.test", 3, 2, 2),
    ("2026006", "Diego", "Morales", "diego@uni.test", 3, 3, 3),
    ("2026007", "Valeria", "Soto", "valeria@uni.test", 1, 2, 3),
    ("2026008", "Mateo", "Rivas", "mateo@uni.test", 2, 1, 4),
]


def init_db():
    conn = get_db()
    conn.executescript("""
    DROP TABLE IF EXISTS users;
    DROP TABLE IF EXISTS students;
    DROP TABLE IF EXISTS grades;
    DROP TABLE IF EXISTS comments;
    DROP TABLE IF EXISTS sedes;
    DROP TABLE IF EXISTS courses;
    DROP TABLE IF EXISTS carreras;
    CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT UNIQUE,
                        password_hash TEXT, role TEXT DEFAULT 'user');
    CREATE TABLE sedes (id INTEGER PRIMARY KEY, name TEXT UNIQUE, city TEXT);
    CREATE TABLE carreras (id INTEGER PRIMARY KEY, code TEXT UNIQUE, name TEXT UNIQUE);
    CREATE TABLE courses (id INTEGER PRIMARY KEY, code TEXT UNIQUE, name TEXT UNIQUE,
                          carrera_id INTEGER REFERENCES carreras(id), ciclo INTEGER);
    CREATE TABLE students (id INTEGER PRIMARY KEY, student_id TEXT UNIQUE,
                           first_name TEXT, last_name TEXT, email TEXT,
                           sede_id INTEGER REFERENCES sedes(id),
                           carrera_id INTEGER REFERENCES carreras(id), ciclo INTEGER);
    CREATE TABLE grades (id INTEGER PRIMARY KEY, student_id TEXT,
                         course TEXT, grade REAL);
    CREATE TABLE comments (id INTEGER PRIMARY KEY, author TEXT, body TEXT,
                           created TEXT DEFAULT CURRENT_TIMESTAMP);
    """)
    conn.execute("INSERT INTO users (email, password_hash, role) VALUES (?,?,?)",
                 ("admin@uni.test", hash_password("Admin123"), "admin"))
    conn.execute("INSERT INTO users (email, password_hash, role) VALUES (?,?,?)",
                 ("ana@uni.test", hash_password("Ana12345"), "user"))
    conn.executemany("INSERT INTO sedes (id, name, city) VALUES (?,?,?)",
                     [(1, "Sede Central", "Apex City"), (2, "Sede Norte", "Valle Norte"),
                      (3, "Sede Occidente", "Puerto Oeste")])
    conn.executemany("INSERT INTO carreras (id, code, name) VALUES (?,?,?)", CARRERAS)
    prefix = {cid: code for cid, code, _ in CARRERAS}
    courses = []
    for cid, ciclos in PENSUM.items():
        for ciclo, names in ciclos.items():
            for n, name in enumerate(names, start=1):
                courses.append((f"{prefix[cid]}{ciclo}0{n}", name, cid, ciclo))
    conn.executemany("INSERT INTO courses (code, name, carrera_id, ciclo) VALUES (?,?,?,?)", courses)
    conn.executemany("INSERT INTO students (student_id, first_name, last_name, email, sede_id, carrera_id, ciclo) "
                     "VALUES (?,?,?,?,?,?,?)", STUDENTS)
    grades = []
    for idx, (sid, _, _, _, _, cid, ciclo_actual) in enumerate(STUDENTS):
        for code, name, c_id, ciclo in courses:
            if c_id == cid and ciclo <= ciclo_actual:
                grades.append((sid, name, 62 + (sum(map(ord, code)) + idx * 7) % 37))
    conn.executemany("INSERT INTO grades (student_id, course, grade) VALUES (?,?,?)", grades)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Base de datos inicializada.")
