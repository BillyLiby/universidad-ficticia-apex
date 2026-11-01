import sqlite3
import hashlib
from config import DB_PATH


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password):
    # DÉBIL A PROPÓSITO (SHA-256 simple, sin sal): se reemplaza en Fase II-A.
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    conn = get_db()
    conn.executescript("""
    DROP TABLE IF EXISTS users;
    DROP TABLE IF EXISTS students;
    DROP TABLE IF EXISTS grades;
    DROP TABLE IF EXISTS comments;
    CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT UNIQUE,
                        password_hash TEXT, role TEXT DEFAULT 'user');
    CREATE TABLE students (id INTEGER PRIMARY KEY, student_id TEXT UNIQUE,
                           first_name TEXT, last_name TEXT, email TEXT);
    CREATE TABLE grades (id INTEGER PRIMARY KEY, student_id TEXT,
                         course TEXT, grade REAL);
    CREATE TABLE comments (id INTEGER PRIMARY KEY, author TEXT, body TEXT,
                           created TEXT DEFAULT CURRENT_TIMESTAMP);
    """)
    conn.execute("INSERT INTO users (email, password_hash, role) VALUES (?,?,?)",
                 ("admin@uni.test", hash_password("Admin123"), "admin"))
    conn.execute("INSERT INTO users (email, password_hash, role) VALUES (?,?,?)",
                 ("ana@uni.test", hash_password("Ana12345"), "user"))
    students = [("2026001", "Ana", "Lopez", "ana@uni.test"),
                ("2026002", "Carlos", "Perez", "carlos@uni.test"),
                ("2026003", "Maria", "Gomez", "maria@uni.test")]
    conn.executemany("INSERT INTO students (student_id, first_name, last_name, email) VALUES (?,?,?,?)", students)
    grades = [("2026001", "Redes", 90), ("2026001", "Seguridad", 85),
              ("2026002", "Redes", 72), ("2026002", "Seguridad", 80),
              ("2026003", "Redes", 95), ("2026003", "Seguridad", 88)]
    conn.executemany("INSERT INTO grades (student_id, course, grade) VALUES (?,?,?)", grades)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Base de datos inicializada.")
