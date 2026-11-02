"""Fase I-C: la salida codifica los datos del usuario (no se interpretan como HTML/JS).
Usa una base de datos temporal."""
import os
import pathlib
import tempfile
import unittest

import db

IMG = "<img src=x onerror=alert(1)>"
SCRIPT = "<script>alert(1)</script>"


class TestXss(unittest.TestCase):
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

    def test_almacenado_se_muestra_como_texto(self):
        self.client.post("/comments", data={"body": IMG})
        for url in ["/lab/xss", "/comments"]:
            html = self.client.get(url).data.decode()
            self.assertNotIn(IMG, html, url)
            self.assertIn("&lt;img src=x onerror=alert(1)&gt;", html, url)

    def test_reflejado_se_muestra_como_texto(self):
        html = self.client.get("/lab/xss", query_string={"q": SCRIPT}).data.decode()
        self.assertNotIn(SCRIPT, html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)

    def test_dom_usa_textcontent_y_no_innerhtml(self):
        js = pathlib.Path("static/js/lab_xss.js").read_text(encoding="utf-8")
        self.assertIn("textContent", js)
        self.assertNotIn("innerHTML", js)

    def test_plantilla_sin_filtro_safe(self):
        tpl = pathlib.Path("templates/lab_xss.html").read_text(encoding="utf-8")
        self.assertNotIn("|safe", tpl)

    def test_cabeceras_csp(self):
        r = self.client.get("/lab/xss")
        csp = r.headers.get("Content-Security-Policy", "")
        self.assertIn("script-src 'self'", csp)
        self.assertNotIn("unsafe-inline", csp.split("style-src")[0])
        self.assertEqual(r.headers.get("X-Content-Type-Options"), "nosniff")

    def test_texto_legitimo_con_simbolos(self):
        self.client.post("/comments", data={"body": "Me gusta <3 & más"})
        html = self.client.get("/comments").data.decode()
        self.assertIn("&lt;3 &amp; más", html)


if __name__ == "__main__":
    unittest.main(verbosity=2)
