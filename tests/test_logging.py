"""Fase II-E: el registro de seguridad nunca contiene datos prohibidos
(contraseñas, tokens, claves, credenciales, teléfonos), y sí registra
los eventos esperados."""
import logging
import os
import tempfile
import unittest
from logging.handlers import RotatingFileHandler

import db
import security_log


class TestSecureLogging(unittest.TestCase):
    FORBIDDEN_SUBSTRINGS = [
        "Admin123", "password", "55011001", "APEX_SECRET_KEY",
        "APEX_DB_PASSWORD", "APEX_ENCRYPTION_KEY", "argon2id",
    ]

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        db.DB_PATH = self.tmp.name
        db.init_db()

        self.log_tmp = tempfile.NamedTemporaryFile(suffix=".log", delete=False)
        self.log_tmp.close()
        security_log.LOG_PATH = self.log_tmp.name
        for h in list(security_log._logger.handlers):
            h.close()
            security_log._logger.removeHandler(h)
        self._handler = RotatingFileHandler(security_log.LOG_PATH, maxBytes=512_000,
                                            backupCount=3, encoding="utf-8")
        self._handler.setFormatter(logging.Formatter("%(message)s"))
        security_log._logger.addHandler(self._handler)

        from app import app
        self.client = app.test_client()

    def tearDown(self):
        # Cerrar el handler ANTES de borrar el archivo: en Windows no se
        # puede eliminar un archivo que sigue abierto por el proceso.
        self._handler.close()
        security_log._logger.removeHandler(self._handler)
        os.unlink(self.tmp.name)
        os.unlink(self.log_tmp.name)

    def log_contents(self):
        with open(security_log.LOG_PATH, encoding="utf-8") as f:
            return f.read()

    def test_login_exitoso_no_filtra_password_ni_token(self):
        r = self.client.post("/login", data={"email": "admin@uni.test", "password": "Admin123"})
        self.assertIn("session", r.headers.get("Set-Cookie", ""))
        contenido = self.log_contents()
        for forbidden in self.FORBIDDEN_SUBSTRINGS:
            self.assertNotIn(forbidden, contenido, forbidden)
        self.assertIn('"event": "login_success"', contenido)
        self.assertIn('"actor": "admin@uni.test"', contenido)

    def test_login_fallido_se_registra_sin_password(self):
        self.client.post("/login", data={"email": "admin@uni.test", "password": "incorrecta123"})
        contenido = self.log_contents()
        self.assertIn('"event": "login_failed"', contenido)
        self.assertNotIn("incorrecta123", contenido)

    def test_expediente_no_registra_telefono(self):
        self.client.post("/login", data={"email": "admin@uni.test", "password": "Admin123"})
        self.client.get("/expediente/2026001")
        contenido = self.log_contents()
        self.assertIn('"event": "expediente_view"', contenido)
        self.assertIn('"target": "2026001"', contenido)
        self.assertNotIn("55011001", contenido)

    def test_alta_de_estudiante_no_registra_telefono(self):
        self.client.post("/login", data={"email": "admin@uni.test", "password": "Admin123"})
        self.client.post("/admin", data={"form": "student", "student_id": "2026077",
                                         "first_name": "Rosa", "last_name": "Diaz",
                                         "email": "rosa@uni.test", "phone": "55019999",
                                         "sede_id": "1", "carrera_id": "1", "ciclo": "1"})
        contenido = self.log_contents()
        self.assertIn('"event": "student_created"', contenido)
        self.assertNotIn("55019999", contenido)

    def test_acceso_admin_denegado_se_registra(self):
        self.client.post("/login", data={"email": "ana@uni.test", "password": "Ana12345"})
        self.client.get("/admin")
        contenido = self.log_contents()
        self.assertIn('"event": "admin_access"', contenido)
        self.assertIn('"outcome": "denied"', contenido)

    def test_inyeccion_de_lineas_de_log_se_sanea(self):
        payload = "atacante@evil.com\\nFAKE_EVENT admin autorizado"
        self.client.post("/login", data={"email": payload, "password": "x"})
        contenido = self.log_contents()
        self.assertNotIn("\nFAKE_EVENT", contenido)

    def test_log_event_rechaza_campos_prohibidos(self):
        with self.assertRaises(ValueError):
            security_log.log_event("x", password="no-deberia-llamarse-asi")

    def test_404_no_se_registra_como_error_de_aplicacion(self):
        self.client.get("/esta-ruta-no-existe")
        contenido = self.log_contents()
        self.assertNotIn('"event": "app_error"', contenido)


if __name__ == "__main__":
    unittest.main(verbosity=2)
