import sqlite3
conn = sqlite3.connect("portal.db")
print(conn.execute("SELECT student_id, phone_encrypted FROM students WHERE student_id='2026001'").fetchone())