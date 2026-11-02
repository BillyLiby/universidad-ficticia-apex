"""Pruebas de integración de la Fase I-A: la aplicación rechaza entradas inválidas
y NO las guarda. Usa una base de datos temporal (no toca portal.db)."""
import os
import tempfile
import unittest

import db


class TestAppValidation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        db.DB_PATH = self.tmp.name
        db.init_db()
        from app import app
        self.client = app.test_client()
        self.client.post("/login", data={"email": "admin@uni.test", "password": "Admin123"})

    def tearDown(self):
        os.unlink(self.tmp.name)

    def count(self, table, where="1=1", params=()):
        conn = db.get_db()
        n = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", params).fetchone()[0]
        conn.close()
        return n

    def grade(self, value, course="Redes", sid="2026001"):
        return self.client.post("/admin", data={"form": "grade", "student_id": sid, "course": course, "grade": value})

    def student(self, **over):
        data = {"form": "student", "student_id": "2026099", "first_name": "Rosa", "last_name": "Diaz",
                "email": "rosa@uni.test", "sede_id": "1", "carrera_id": "1", "ciclo": "1"}
        data.update(over)
        return self.client.post("/admin", data=data)

    def test_nota_fuera_de_rango_rechazada(self):
        before = self.count("grades")
        for bad in ["150", "-5", "abc", "nan"]:
            self.assertIn("inválidos".encode(), self.grade(bad).data, bad)
        self.assertEqual(self.count("grades"), before)

    def test_nota_valida_aceptada(self):
        before = self.count("grades")
        self.assertIn(b"agregada", self.grade("88").data)
        self.assertEqual(self.count("grades"), before + 1)

    def test_estudiante_invalido_rechazado(self):
        before = self.count("students")
        for over in [{"student_id": "abc"}, {"first_name": "<b>Hack</b>"}, {"last_name": "Diaz'; DROP TABLE users;--"},
                     {"email": "no-es-correo"}, {"sede_id": "99"}, {"carrera_id": "x"}, {"ciclo": "50"}]:
            self.assertIn("inválidos".encode(), self.student(**over).data, over)
        self.assertEqual(self.count("students"), before)

    def test_estudiante_valido_aceptado(self):
        before = self.count("students")
        self.assertIn(b"agregado", self.student(first_name="Jos\xe9 Luis", last_name="O'Connor").data)
        self.assertEqual(self.count("students"), before + 1)

    def test_busqueda_invalida_rechazada(self):
        for q in ["<script>alert(1)</script>", "x; DROP TABLE users", "a" * 60]:
            r = self.client.get("/search", query_string={"q": q})
            self.assertIn("inválido".encode(), r.data, q)
        self.assertEqual(self.client.get("/search?q=Ana").status_code, 200)

    def test_id_expediente_invalido(self):
        r = self.client.get("/expediente/abc", follow_redirects=True)
        self.assertIn("inválido".encode(), r.data)

    def test_parametros_de_filtro_no_rompen(self):
        for url in ["/students?sede=%C2%B2", "/students?carrera=abc", "/courses?carrera=%C2%B2"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_registro_valida_correo_y_clave(self):
        before = self.count("users")
        self.client.post("/register", data={"email": "mal", "password": "abc"})
        self.client.post("/register", data={"email": "ok@uni.test", "password": "sololetras"})
        self.assertEqual(self.count("users"), before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
