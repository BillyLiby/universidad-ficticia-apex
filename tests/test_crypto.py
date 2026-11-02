"""Fase II-B: cifrado de datos en reposo con Fernet.
- El cifrado de un mismo texto produce resultados distintos cada vez (IV aleatorio).
- El descifrado recupera exactamente el texto original.
- Un token alterado se rechaza (verificación de integridad vía HMAC).
- La clave se toma SIEMPRE de la variable de entorno, nunca de un valor fijo en el código.
"""
import os
import pathlib
import tempfile
import unittest

import crypto_utils
import db


class TestCrypto(unittest.TestCase):
    def setUp(self):
        crypto_utils._fernet.cache_clear()
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        db.DB_PATH = self.tmp.name
        db.init_db()
        from app import app
        self.client = app.test_client()
        self.client.post("/login", data={"email": "admin@uni.test", "password": "Admin123"})

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_cifrados_del_mismo_texto_son_distintos(self):
        t1 = crypto_utils.encrypt_field("55011234")
        t2 = crypto_utils.encrypt_field("55011234")
        self.assertNotEqual(t1, t2)

    def test_descifrado_recupera_el_original(self):
        token = crypto_utils.encrypt_field("55011234")
        self.assertEqual(crypto_utils.decrypt_field(token), "55011234")

    def test_token_alterado_se_rechaza(self):
        token = crypto_utils.encrypt_field("55011234")
        alterado = token[:-1] + ("A" if token[-1] != "A" else "B")
        self.assertIsNone(crypto_utils.decrypt_field(alterado))

    def test_telefono_se_guarda_cifrado_en_la_bd(self):
        conn = db.get_db()
        row = conn.execute("SELECT phone_encrypted FROM students WHERE student_id = '2026001'").fetchone()
        conn.close()
        self.assertIsNotNone(row["phone_encrypted"])
        self.assertNotIn("55011001", row["phone_encrypted"])

    def test_expediente_muestra_el_telefono_descifrado(self):
        html = self.client.get("/expediente/2026001").data.decode()
        self.assertIn("55011001", html)

    def test_sin_clave_de_entorno_falla_explicitamente(self):
        guardada = os.environ.pop(crypto_utils.ENV_VAR, None)
        crypto_utils._fernet.cache_clear()
        try:
            with self.assertRaises(RuntimeError):
                crypto_utils.encrypt_field("x")
        finally:
            if guardada:
                os.environ[crypto_utils.ENV_VAR] = guardada
            crypto_utils._fernet.cache_clear()

    def test_clave_no_esta_escrita_en_el_codigo_fuente(self):
        src = pathlib.Path("crypto_utils.py").read_text(encoding="utf-8")
        self.assertNotIn("Fernet(b'", src)
        self.assertIn("os.environ", src)

    def test_alta_de_estudiante_valida_telefono(self):
        r = self.client.post("/admin", data={"form": "student", "student_id": "2026050",
                                             "first_name": "Rosa", "last_name": "Diaz",
                                             "email": "rosa@uni.test", "phone": "123",
                                             "sede_id": "1", "carrera_id": "1", "ciclo": "1"})
        self.assertIn("inv\u00e1lidos".encode(), r.data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
