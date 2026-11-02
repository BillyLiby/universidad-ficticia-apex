"""Fase I-B: la consulta parametrizada no permite alterar la estructura SQL.
Usa una base de datos temporal y NO valida la entrada, para aislar el efecto
de la parametrización."""
import os
import tempfile
import unittest

import db

PAYLOAD_OR = "' OR 1=1--"
PAYLOAD_UNION = "' UNION SELECT id, email, password_hash, role FROM users--"
SQL_FIJA = "WHERE first_name LIKE ? OR last_name LIKE ?"


class TestSqlInjection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        db.DB_PATH = self.tmp.name
        db.init_db()
        conn = db.get_db()
        conn.execute("INSERT INTO students (student_id, first_name, last_name, email, sede_id, carrera_id, ciclo) "
                     "VALUES (?,?,?,?,?,?,?)", ("2026099", "Sean", "O'Connor", "sean@uni.test", 1, 1, 1))
        conn.commit()
        conn.close()
        from app import app
        self.client = app.test_client()
        self.client.post("/login", data={"email": "admin@uni.test", "password": "Admin123"})

    def tearDown(self):
        os.unlink(self.tmp.name)

    def lab(self, q):
        r = self.client.get("/lab/search", query_string={"q": q})
        self.assertEqual(r.status_code, 200)
        return r.data.decode()

    def filas(self, html):
        return html.count("<tr><td>")

    def test_busqueda_normal(self):
        self.assertEqual(self.filas(self.lab("Ana")), 1)

    def test_or_1_igual_1_no_devuelve_todo(self):
        html = self.lab(PAYLOAD_OR)
        self.assertEqual(self.filas(html), 0)
        self.assertNotIn("Error SQL", html)

    def test_union_no_expone_usuarios(self):
        html = self.lab(PAYLOAD_UNION)
        self.assertEqual(self.filas(html), 0)
        self.assertNotIn("password_hash", html.split("Parámetros")[0].split("Sentencia ejecutada")[-1].replace("students", ""))
        self.assertNotIn("8c6976e5b5410415", html)

    def test_comilla_no_rompe_la_sentencia(self):
        html = self.lab("Ana'")
        self.assertNotIn("syntax error", html)
        self.assertNotIn("Error SQL", html)

    def test_la_sentencia_no_cambia_con_la_entrada(self):
        for q in ["Ana", PAYLOAD_OR, PAYLOAD_UNION, "Ana'"]:
            self.assertIn(SQL_FIJA, self.lab(q), q)
            self.assertNotIn("UNION", self.lab(q).split("Parámetros")[0].split("Sentencia ejecutada")[-1], q)

    def test_dato_legitimo_con_apostrofe_funciona(self):
        self.assertEqual(self.filas(self.lab("O'Connor")), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
