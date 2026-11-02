"""Fase I-D: la compresión no invoca ninguna shell del sistema operativo.
El nombre de archivo se valida con lista blanca y la escritura queda
confinada a reports/. Usa una base de datos temporal."""
import os
import pathlib
import tempfile
import unittest
import zipfile

import db


class TestCommandInjection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        db.DB_PATH = self.tmp.name
        db.init_db()
        from app import app, REPORTS_DIR
        self.app = app
        self.reports_dir = REPORTS_DIR
        self.before = set(os.listdir(self.reports_dir))
        self.client = app.test_client()
        self.client.post("/login", data={"email": "admin@uni.test", "password": "Admin123"})

    def tearDown(self):
        os.unlink(self.tmp.name)
        for f in set(os.listdir(self.reports_dir)) - self.before:
            os.remove(os.path.join(self.reports_dir, f))
        report_csv = os.path.join(os.path.dirname(self.reports_dir), "report.csv")
        if os.path.exists(report_csv):
            os.remove(report_csv)

    def nuevos_archivos(self):
        return set(os.listdir(self.reports_dir)) - self.before

    def test_nombre_valido_genera_zip_con_el_reporte(self):
        r = self.client.post("/lab/compress", data={"filename": "reporte_test"})
        self.assertIn(b"Comprimido correctamente", r.data)
        self.assertEqual(self.nuevos_archivos(), {"reporte_test.zip"})
        zpath = os.path.join(self.reports_dir, "reporte_test.zip")
        with zipfile.ZipFile(zpath) as zf:
            self.assertEqual(zf.namelist(), ["report.csv"])

    def test_separador_de_comandos_rechazado_y_sin_archivo_extra(self):
        payload = "a.zip & whoami > pwned.txt &"
        r = self.client.post("/lab/compress", data={"filename": payload})
        self.assertIn(b"inv\xc3\xa1lido", r.data)
        self.assertEqual(self.nuevos_archivos(), set())

    def test_recorrido_de_rutas_rechazado(self):
        for payload in ["../fuera", "..\\fuera", "a/b", "a\\b", "/etc/passwd"]:
            r = self.client.post("/lab/compress", data={"filename": payload})
            self.assertIn(b"inv\xc3\xa1lido", r.data, payload)
        self.assertEqual(self.nuevos_archivos(), set())

    def test_caracteres_especiales_varios_rechazados(self):
        for payload in ["a;b", "a|b", "a`b", "a$b", "a b", "a'b", 'a"b', "a" * 41]:
            r = self.client.post("/lab/compress", data={"filename": payload})
            self.assertIn(b"inv\xc3\xa1lido", r.data, payload)
        self.assertEqual(self.nuevos_archivos(), set())

    def test_no_se_invoca_ninguna_shell(self):
        src = pathlib.Path("app.py").read_text(encoding="utf-8")
        fase_d = src[src.index("FILENAME_RE"):]
        self.assertNotIn("shell=True", fase_d)
        self.assertNotIn("subprocess", fase_d)
        self.assertNotIn("os.system", fase_d)

    def test_resultado_siempre_dentro_de_reports(self):
        from app import REPORTS_DIR
        r = self.client.post("/lab/compress", data={"filename": "otro_valido"})
        self.assertIn(b"Comprimido correctamente", r.data)
        zpath = os.path.abspath(os.path.join(REPORTS_DIR, "otro_valido.zip"))
        self.assertTrue(zpath.startswith(os.path.abspath(REPORTS_DIR) + os.sep))


if __name__ == "__main__":
    unittest.main(verbosity=2)
